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
            ("retries", "INTEGER NOT NULL DEFAULT 0"),
            ("trigger_start", "INTEGER NOT NULL DEFAULT 0"),
            ("trigger_stop", "INTEGER NOT NULL DEFAULT 0")
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
    if job_id is not None and job_id in _running_processes:
        return "ALREADY_RUNNING"
        
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
    start_time = time.time()
    
    log_file_path = None
    log_f = None
    if job_id is not None:
        log_dir = "logs"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"job_{job_id}_{log_id}_{ts_str}.log"
        log_file_path = os.path.join(log_dir, log_filename)
        log_f = open(log_file_path, "w", encoding="utf-8", errors="replace")
        log_f.write(f"--- CRONVAULT REAL-TIME LOG ---\n")
        log_f.write(f"Command: {command}\n")
        log_f.write(f"Start: {datetime.now().isoformat()}\n")
        log_f.write(f"Timeout: {timeout_mins} min.\n")
        log_f.write(f"-------------------------------\n\n")
        log_f.flush()

    status = "FAIL"
    full_output = []

    for attempt in range(retries + 1):
        if attempt > 0:
            msg = f"\n[!] Reintento {attempt}/{retries} iniciándose...\n"
            if log_f: log_f.write(msg); log_f.flush()
            full_output.append(msg)

        try:
            process = subprocess.Popen(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                stdin=subprocess.DEVNULL,
                text=True,
                encoding='utf-8', 
                errors='replace',
                bufsize=1
            )
            
            if job_id is not None:
                _running_processes[job_id] = process

            last_db_update = time.time()
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    ts = datetime.now().strftime("%H:%M:%S")
                    formatted_line = f"[{ts}] {line}"
                    if log_f:
                        log_f.write(formatted_line)
                        log_f.flush()
                    full_output.append(line)
                
                if time.time() - last_db_update > 10:
                    if log_id is not None:
                        partial_text = "".join(full_output)[-16000:]
                        conn = get_conn()
                        with _db_lock:
                            conn.execute("UPDATE logs SET output=? WHERE id=?", (partial_text, log_id))
                            conn.commit()
                    last_db_update = time.time()
                
                if time.time() - start_time > timeout_secs:
                    process.terminate()
                    err_msg = f"\n[TIMEOUT] Proceso detenido tras {timeout_mins} minutos.\n"
                    if log_f: log_f.write(err_msg); log_f.flush()
                    full_output.append(err_msg)
                    break

            return_code = process.poll()
            status = "OK" if return_code == 0 else "FAIL"
            
            if job_id in _manual_stops:
                status = "DETENIDO"
                _manual_stops.discard(job_id)
                err_msg = f"\n[STOP] Proceso detenido manualmente por el usuario.\n"
                if log_f: log_f.write(err_msg); log_f.flush()
                full_output.append(err_msg)

            if job_id is not None:
                _running_processes.pop(job_id, None)
            
            if status == "OK" or status == "DETENIDO":
                break
            elif attempt < retries:
                time.sleep(10)

        except Exception as e:
            err_msg = f"\nError en ejecución: {str(e)}\n"
            if log_f: log_f.write(err_msg); log_f.flush()
            full_output.append(err_msg)
            status = "FAIL"

    if log_f:
        log_f.write(f"\n-------------------------------\n")
        log_f.write(f"Finalizado: {datetime.now().isoformat()}\n")
        log_f.write(f"Estado Final: {status}\n")
        log_f.close()

    combined_text = "".join(full_output)
    db_summary = combined_text[:16000]

    if log_id is not None:
        conn = get_conn()
        with _db_lock:
            conn.execute(
                "UPDATE logs SET output=?, status=? WHERE id=?",
                (db_summary, status, log_id),
            )
            conn.commit()
        _rotate_logs(job_id)

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
            
    MAX_PHYSICAL_LOGS = 10
    log_dir = "logs"
    if os.path.exists(log_dir):
        try:
            prefix = f"job_{job_id}_"
            log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.startswith(prefix) and f.endswith(".log")]
            if len(log_files) > MAX_PHYSICAL_LOGS:
                log_files.sort(key=os.path.getmtime)
                for file_path in log_files[:-MAX_PHYSICAL_LOGS]:
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        except Exception:
            pass

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
            config = (
                r["command"], r["day"], r["month"], r["day_of_week"],
                r["hour"], r["minute"], r["timeout_mins"],
                r["max_instances"], r["retries"]
            )
            
            if sid in _job_cache and _job_cache[sid] == config:
                continue

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

_running_processes = {}
_manual_stops = set()

def check_triggers():
    rows = db_read("SELECT id, trigger_start, trigger_stop FROM jobs WHERE trigger_start = 1 OR trigger_stop = 1")
    for r in rows:
        job_id = r["id"]
        
        if r["trigger_stop"]:
            db_write("UPDATE jobs SET trigger_stop = 0 WHERE id=?", (job_id,))
            if job_id in _running_processes:
                _manual_stops.add(job_id)
                try:
                    _running_processes[job_id].terminate()
                except Exception:
                    pass
        
        if r["trigger_start"]:
            db_write("UPDATE jobs SET trigger_start = 0 WHERE id=?", (job_id,))
            if job_id in _running_processes:
                continue
                
            job_rows = db_read("SELECT command, timeout_mins, retries FROM jobs WHERE id=?", (job_id,))
            if job_rows:
                cmd = job_rows[0]["command"]
                tmo = job_rows[0]["timeout_mins"]
                ret = job_rows[0]["retries"]
                threading.Thread(target=run_command, args=(cmd, job_id, tmo, ret), daemon=True).start()

def run_service():
    init_db()
    scheduler.start()
    log_file = os.path.join(os.path.dirname(__file__), "service.log")
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] CronVault service started\n")
    
    last_sync = 0
    try:
        while True:
            if time.time() - last_sync >= 15:
                sync_jobs()
                last_sync = time.time()
                
            check_triggers()
            time.sleep(3)
    except KeyboardInterrupt:
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] Service shutting down...\n")
        shutdown_scheduler()