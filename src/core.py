import sys
import os
import time
import sqlite3
import threading
import subprocess
import atexit
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

IS_SERVICE = "--service" in sys.argv
DB_PATH = "jobs.db"
MAX_LOGS_PER_JOB = 1000

_db_lock = threading.Lock()
_local   = threading.local()

def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn

def init_db():
    conn = get_conn()
    with _db_lock:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                command       TEXT    NOT NULL,
                labels        TEXT    NOT NULL DEFAULT '',
                day           TEXT    NOT NULL DEFAULT '*',
                month         TEXT    NOT NULL DEFAULT '*',
                day_of_week   TEXT    NOT NULL DEFAULT '*',
                hour          INTEGER NOT NULL,
                minute        INTEGER NOT NULL,
                timeout_mins  INTEGER NOT NULL DEFAULT 20,
                max_instances INTEGER NOT NULL DEFAULT 1,
                retries       INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id     INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                output     TEXT,
                error      TEXT,
                status     TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            );
        """)
        cols_to_add = [
            ("timeout_mins", "INTEGER NOT NULL DEFAULT 20"),
            ("max_instances", "INTEGER NOT NULL DEFAULT 1"),
            ("day", "TEXT NOT NULL DEFAULT '*'"),
            ("month", "TEXT NOT NULL DEFAULT '*'"),
            ("day_of_week", "TEXT NOT NULL DEFAULT '*'"),
            ("retries", "INTEGER NOT NULL DEFAULT 0")
        ]
        for col_name, col_def in cols_to_add:
            try:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass
        conn.commit()

def db_write(sql: str, params: tuple = ()):
    conn = get_conn()
    with _db_lock:
        conn.execute(sql, params)
        conn.commit()

def db_read(sql: str, params: tuple = ()):
    return get_conn().execute(sql, params).fetchall()

def run_command(command: str, job_id: int | None = None, timeout_mins: int = 20, retries: int = 0):
    log_id = None
    if job_id is not None:
        conn = get_conn()
        with _db_lock:
            cur = conn.execute(
                "INSERT INTO logs (job_id, output, error, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, "", "", "RUNNING", datetime.now().isoformat()),
            )
            log_id = cur.lastrowid
            conn.commit()

    timeout_secs = timeout_mins * 60
    final_out, final_err = "", ""
    status = "FAIL"

    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout_secs
            )
            status = "OK" if result.returncode == 0 else "FAIL"
            out, err = result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            status, out, err = "FAIL", "", f"Timeout: proceso excedió {timeout_mins} min."
        except Exception as e:
            status, out, err = "FAIL", "", str(e)

        if status != "OK" and attempt < retries:
            final_out += out
            final_err += f"{err}\n\n[!] Intento {attempt + 1}/{retries + 1} fallido. Reintentando en 30s...\n"
            time.sleep(30)
        else:
            final_out += out
            final_err += err
            break 

    # Save full logs to file
    if job_id is not None:
        log_dir = "logs"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{log_id}" if log_id else ""
        log_filename = f"job_{job_id}{suffix}_{ts_str}.log"
        log_file_path = os.path.join(log_dir, log_filename)
        
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(f"--- CRONVAULT FULL LOG ---\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Job ID: {job_id}\n")
            f.write(f"Command: {command}\n")
            f.write(f"Status: {status}\n")
            f.write(f"--------------------------\n\n")
            f.write(f"STDOUT:\n{final_out}\n\n")
            f.write(f"STDERR:\n{final_err}\n")

    # DB records summary (truncated)
    db_out = final_out[:8000]
    db_err = final_err[:8000]

    if log_id is not None:
        conn = get_conn()
        with _db_lock:
            conn.execute(
                "UPDATE logs SET output=?, error=?, status=? WHERE id=?",
                (db_out, db_err, status, log_id),
            )
            conn.commit()

        _rotate_logs(job_id)
    elif job_id is not None:
        db_write(
            "INSERT INTO logs (job_id, output, error, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, db_out, db_err, status, datetime.now().isoformat()),
        )

    return status

def _rotate_logs(job_id: int):
    conn = get_conn()
    with _db_lock:
        rows = conn.execute(
            "SELECT COUNT(*) AS cnt FROM logs WHERE job_id=?", (job_id,)
        ).fetchone()
        excess = rows["cnt"] - MAX_LOGS_PER_JOB
        if excess > 0:
            conn.execute("""
                DELETE FROM logs WHERE id IN (
                    SELECT id FROM logs WHERE job_id=? ORDER BY id ASC LIMIT ?
                )
            """, (job_id, excess))
            conn.commit()

scheduler = BackgroundScheduler(daemon=True)
_scheduled_ids: set = set()
_scheduler_lock = threading.Lock()
_job_cache = {}

def sync_jobs():
    rows   = db_read("SELECT id, command, day, month, day_of_week, hour, minute, timeout_mins, max_instances, retries FROM jobs")
    db_ids = {str(r["id"]) for r in rows}
    with _scheduler_lock:
        for sid in list(_scheduled_ids):
            if sid not in db_ids:
                try:    scheduler.remove_job(sid)
                except: pass
                _scheduled_ids.discard(sid)
                _job_cache.pop(sid, None)
        
        for r in rows:
            sid = str(r["id"])
            # Create a simple config tuple to check for changes
            config = (
                r["command"], r["day"], r["month"], r["day_of_week"],
                r["hour"], r["minute"], r["timeout_mins"],
                r["max_instances"], r["retries"]
            )
            
            if sid in _job_cache and _job_cache[sid] == config:
                continue # No changes, skip add_job

            scheduler.add_job(
                run_command, "cron",
                id=sid,
                day=r["day"],
                month=r["month"],
                day_of_week=r["day_of_week"],
                hour=r["hour"],
                minute=r["minute"],
                args=[r["command"], r["id"], r["timeout_mins"], r["retries"]],
                max_instances=r["max_instances"],
                replace_existing=True,
            )
            _scheduled_ids.add(sid)
            _job_cache[sid] = config

def remove_scheduled_job(job_id: int):
    sid = str(job_id)
    with _scheduler_lock:
        try:    scheduler.remove_job(sid)
        except: pass
        _scheduled_ids.discard(sid)

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)

atexit.register(shutdown_scheduler)

def run_service():
    init_db()
    scheduler.start()
    log_file = os.path.join(os.path.dirname(__file__), "service.log")
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] CronVault service started\n")
    
    try:
        while True:
            with open(log_file, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] Syncing jobs...\n")
            sync_jobs()
            with open(log_file, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] Jobs synced. Next sync in 30s\n")
            time.sleep(30)
    except KeyboardInterrupt:
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] Service shutting down...\n")
        shutdown_scheduler()