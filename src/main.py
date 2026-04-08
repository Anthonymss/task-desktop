import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTableWidget,
    QTableWidgetItem, QTextEdit, QMessageBox, QDialog, QHeaderView
)
from PySide6.QtGui import QColor, QKeySequence, QFont, QPalette, QShortcut, QIcon
from PySide6.QtCore import Qt, QTimer, QThread, Signal

import core
from ui_components import C, StatCard, JobDialog, ChipsWidget

def get_resource_path(filename):
    """Find resource file in current dir or resources/ subdir."""
    resource_paths = [
        filename,
        os.path.join(os.path.dirname(__file__), '..', 'resources', filename),
    ]
    if hasattr(sys, '_MEIPASS'):
        resource_paths.insert(0, os.path.join(sys._MEIPASS, filename))
    
    for path in resource_paths:
        if os.path.exists(path):
            return path
    return filename 
class LogDialog(QDialog):
    def __init__(self, job_id, job_name, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.setWindowTitle(f"Monitor de Log: {job_name}")
        self.resize(800, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10) if sys.platform == "win32" else QFont("Monospace", 10))
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {C['log_bg']};
                color: {C['log_text']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout.addWidget(self.log_view)
        
        btn_layout = QHBoxLayout()
        self.status_lbl = QLabel("Buscando archivo de log...")
        self.status_lbl.setStyleSheet(f"color: {C['text_secondary']}; font-size: 11px;")
        btn_layout.addWidget(self.status_lbl)
        btn_layout.addStretch()
        
        btn_close = QPushButton("Cerrar")
        btn_close.setFixedHeight(32)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['bg']};
                border: 1.5px solid {C['border']};
                border-radius: 6px;
                padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {C['border']}; }}
        """)
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        self.log_file = self._find_latest_log()
        self.last_pos = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_logs)
        self.timer.start(1000)
        
        if self.log_file:
            self._update_logs()
        else:
            self.log_view.append("No se encontró ningún archivo de log para este Job.\nEjecútalo primero para generar logs.")

    def _find_latest_log(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return None
        
        prefix = f"job_{self.job_id}_"
        logs = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.startswith(prefix) and f.endswith(".log")]
        if not logs:
            return None
        
        return max(logs, key=os.path.getmtime)

    def _update_logs(self):
        if not self.log_file:
            self.log_file = self._find_latest_log()
            if not self.log_file: return
            self.log_view.clear()
            self.status_lbl.setText(f"Monitoreando: {os.path.basename(self.log_file)}")

        if not os.path.exists(self.log_file):
            return

        try:
            curr_size = os.path.getsize(self.log_file)
            if curr_size > self.last_pos:
                with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self.last_pos)
                    new_data = f.read()
                    if new_data:
                        self.log_view.append(new_data.strip())
                    self.last_pos = f.tell()
                self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
            
            self.status_lbl.setText(f"Monitoreando: {os.path.basename(self.log_file)} ({os.path.getsize(self.log_file)//1024} KB)")
        except Exception as e:
            self.status_lbl.setText(f"Error leyendo log: {str(e)}")

class App(QWidget):
    COLS = ["ID", "Nombre", "Comando", "Labels", "Programación", "Estado", "Última ejecución", "Acciones"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CronVault")
        self.resize(1240, 740)
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(f"QWidget {{ background-color: {C['bg']}; }}")

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        header.setFixedHeight(58)
        header.setStyleSheet(
            f"background-color:{C['surface']};"
            f"border-bottom:1px solid {C['border']};"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("🔒  CronVault")
        logo.setStyleSheet(
            f"font-size:15px;font-weight:700;color:{C['text']};"
            f"background:transparent;border:none;"
        )

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Buscar por nombre o label…")
        self.search.setFixedWidth(280)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: {C['bg']};
                border: 1.5px solid {C['border']};
                border-radius: 20px;
                padding: 6px 16px;
                font-size: 13px;
                color: {C['text']};
            }}
            QLineEdit:focus {{ border-color: {C['accent']}; }}
        """)
        self.search.textChanged.connect(self.load_jobs)

        h_lay.addWidget(logo)
        h_lay.addStretch()
        h_lay.addWidget(self.search)
        root.addWidget(header)

        body = QWidget()
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(24, 18, 24, 18)
        b_lay.setSpacing(14)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.card_total   = StatCard("TOTAL JOBS",  "0", C["accent"])
        self.card_ok      = StatCard("EXITOSOS",    "0", C["success"])
        self.card_fail    = StatCard("FALLIDOS",    "0", C["danger"])
        self.card_running = StatCard("EN CURSO",    "0", C["warn"])
        self.card_pend    = StatCard("PENDIENTES",  "0", C["text_muted"])
        for card in (self.card_total, self.card_ok, self.card_fail,
                     self.card_running, self.card_pend):
            stats_row.addWidget(card)
        b_lay.addLayout(stats_row)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.btn_add     = self._mk_btn("＋  Nuevo job",      kind="primary")
        self.btn_edit    = self._mk_btn("✏  Editar")
        self.btn_clrlogs = self._mk_btn("🧹  Limpiar logs")
        self.btn_delete  = self._mk_btn("✕  Eliminar",         kind="danger")
        for btn in (self.btn_add, self.btn_edit, self.btn_clrlogs, self.btn_delete):
            toolbar.addWidget(btn)
        toolbar.addStretch()
        b_lay.addLayout(toolbar)


        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {C['surface']};
                alternate-background-color: {C['surface2']};
                border: 1.5px solid {C['border']};
                border-radius: 12px;
                font-size: 13px;
                color: {C['text']};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 4px 10px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {C['accent_light']};
                color: {C['accent']};
            }}
            QHeaderView::section {{
                background-color: {C['surface2']};
                color: {C['text_muted']};
                border: none;
                border-bottom: 1.5px solid {C['border']};
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.6px;
            }}
            QScrollBar:vertical {{
                background: {C['bg']};
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        b_lay.addWidget(self.table)

        log_hdr = QHBoxLayout()
        log_title = QLabel("📋  Historial")
        log_title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{C['text']};"
            f"background:transparent;border:none;"
        )
        self.log_job_name = QLabel("")
        self.log_job_name.setStyleSheet(
            f"font-size:12px;color:{C['text_muted']};"
            f"background:transparent;border:none;"
        )
        self.btn_log_details = QPushButton("Ver detalles")
        self.btn_log_details.setFixedHeight(26)
        self.btn_log_details.setEnabled(False)
        self.btn_log_details.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['surface']};
                color: {C['text_secondary']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {C['bg']}; }}
        """)
        self.btn_log_details.clicked.connect(self._show_log_details)
        log_hdr.addWidget(log_title)
        log_hdr.addWidget(self.log_job_name)
        log_hdr.addStretch()
        log_hdr.addWidget(self.btn_log_details)
        b_lay.addLayout(log_hdr)

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setFixedHeight(200)
        self.logs.setPlaceholderText("Selecciona un job para ver su historial…")
        self.logs.setStyleSheet(f"""
            QTextEdit {{
                background-color: {C['log_bg']};
                color: {C['log_text']};
                border: 1.5px solid {C['border']};
                border-radius: 10px;
                padding: 12px 16px;
                font-family: 'Cascadia Code', 'Consolas', 'Menlo', monospace;
                font-size: 12px;
            }}
        """)
        b_lay.addWidget(self.logs)

        root.addWidget(body)

        self.btn_add.clicked.connect(self.add_job)
        self.btn_edit.clicked.connect(self.edit_job)
        self.btn_delete.clicked.connect(self.delete_job)
        self.btn_clrlogs.clicked.connect(self.clear_logs)
        self.table.itemSelectionChanged.connect(self.load_logs)
        self.table.doubleClicked.connect(self.edit_job)

        self._last_log_rows = []
        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(self.delete_job)

        self._timer = QTimer(self)
        self._timer.setInterval(10_000)
        self._timer.timeout.connect(self._auto_refresh)
        self._timer.start()

        self.load_jobs()
        core.sync_jobs()
        self._autoselect_last_job()

    def _mk_btn(self, text: str, kind: str = "default") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        if kind == "primary":
            s = f"""
                QPushButton {{
                    background-color: {C['accent']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 0 18px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {C['accent_hover']}; }}
                QPushButton:disabled {{ background-color: #a5b4fc; }}
            """
        elif kind == "danger":
            s = f"""
                QPushButton {{
                    background-color: {C['danger_light']};
                    color: {C['danger']};
                    border: 1.5px solid #fecaca;
                    border-radius: 8px;
                    padding: 0 16px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: #fee2e2; }}
            """
        else:
            s = f"""
                QPushButton {{
                    background-color: {C['surface']};
                    color: {C['text']};
                    border: 1.5px solid {C['border']};
                    border-radius: 8px;
                    padding: 0 16px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {C['accent_light']};
                    border-color: {C['accent']};
                    color: {C['accent']};
                }}
                QPushButton:disabled {{
                    color: {C['text_muted']};
                    border-color: {C['border']};
                    background-color: {C['bg']};
                }}
            """
        btn.setStyleSheet(s)
        return btn

    def _autoselect_last_job(self):
        rows = core.db_read("SELECT job_id FROM logs ORDER BY id DESC LIMIT 1")
        if rows:
            self._select_job_by_id(rows[0]["job_id"])
            self.load_logs()

    def _select_job_by_id(self, job_id: int):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and int(item.text()) == job_id:
                self.table.selectRow(row)
                return

    def load_jobs(self):
        keyword = self.search.text().strip()
        where, params = "", ()
        if keyword:
            where  = "WHERE j.name LIKE ? OR j.labels LIKE ?"
            params = (f"%{keyword}%", f"%{keyword}%")

        jobs = core.db_read(f"""
            SELECT j.*,
                   l.status     AS last_status,
                   l.created_at AS last_run
            FROM jobs j
            LEFT JOIN logs l ON l.id = (
                SELECT id FROM logs WHERE job_id = j.id ORDER BY id DESC LIMIT 1
            )
            {where}
            ORDER BY j.id
        """, params)

        current_id = self._get_selected_id()
        self.table.setRowCount(0)
        total_ok = total_fail = total_pend = total_running = 0

        for i, job in enumerate(jobs):
            job = dict(job) 
            self.table.insertRow(i)
            status   = job["last_status"] or "—"
            last_run = (job["last_run"] or "—")[:19].replace("T", "  ")

            if status == "OK":      total_ok      += 1
            elif status == "FAIL":  total_fail    += 1
            elif status == "RUNNING": total_running += 1
            else:                   total_pend    += 1

            self.table.setItem(i, 0, QTableWidgetItem(str(job["id"])))

            name_item = QTableWidgetItem(job["name"])
            name_item.setForeground(QColor(C["text"]))
            self.table.setItem(i, 1, name_item)

            cmd_item = QTableWidgetItem(job["command"])
            cmd_item.setForeground(QColor(C["text_secondary"]))
            self.table.setItem(i, 2, cmd_item)

            labels = [l.strip() for l in job["labels"].split(",") if l.strip()]
            self.table.setCellWidget(i, 3, ChipsWidget(labels))

            d, m, dw = job.get('day','*'), job.get('month','*'), job.get('day_of_week','*')
            cron_str = f"{job['hour']:02d}:{job['minute']:02d}"
            
            extras = []
            if d != '*': extras.append(f"D:{d}")
            if m != '*': extras.append(f"M:{m}")
            if dw != '*': extras.append(f"W:{dw}")
            
            if extras:
                cron_str += f" ({', '.join(extras)})"

            hora_item = QTableWidgetItem(cron_str)
            hora_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, hora_item)

            st_item = QTableWidgetItem(f"  {status}  ")
            st_item.setTextAlignment(Qt.AlignCenter)
            if status == "OK":
                st_item.setForeground(QColor(C["success"]))
                st_item.setBackground(QColor(C["success_light"]))
            elif status == "FAIL":
                st_item.setForeground(QColor(C["danger"]))
                st_item.setBackground(QColor(C["danger_light"]))
            elif status == "RUNNING":
                st_item.setForeground(QColor(C["warn"]))
                st_item.setBackground(QColor(C["warn_light"]))
            elif status == "DETENIDO":
                st_item.setForeground(QColor(C["danger"]))
                st_item.setBackground(QColor(C["surface2"]))
            else:
                st_item.setForeground(QColor(C["text_muted"]))
            self.table.setItem(i, 5, st_item)

            lr_item = QTableWidgetItem(last_run)
            lr_item.setForeground(QColor(C["text_muted"]))
            self.table.setItem(i, 6, lr_item)

            container = QWidget()
            lay = QHBoxLayout(container)
            lay.setContentsMargins(5, 0, 5, 0)
            lay.setSpacing(6)
            lay.setAlignment(Qt.AlignCenter)

            style_btn = f"""
                QPushButton {{
                    background-color: {C['bg']}; color: {C['accent']};
                    border: 1px solid {C['border']}; border-radius: 4px; font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {C['accent_light']}; border-color: {C['accent']}; }}
            """

            jid, jname = job["id"], job["name"]
            
            btn_play = QPushButton(" ▶ ")
            btn_play.setToolTip("Inicia el job inmediatamente en segundo plano")
            btn_play.setFixedSize(30, 26)
            btn_play.setStyleSheet(style_btn)
            btn_play.clicked.connect(lambda checked=False, id=jid, name=jname: self._trigger_job_action(id, name, "start"))
            
            btn_stop = QPushButton(" ⏹ ")
            btn_stop.setToolTip("Detiene el job si está en ejecución")
            btn_stop.setFixedSize(30, 26)
            btn_stop.setStyleSheet(f"""
                QPushButton {{ background-color: {C['bg']}; color: {C['danger']}; border: 1px solid {C['border']}; border-radius: 4px; font-size: 14px; }}
                QPushButton:hover {{ background-color: {C['danger_light']}; border-color: {C['danger']}; }}
                QPushButton:disabled {{ color: {C['border']}; border-color: {C['border']}; }}
            """)
            btn_stop.clicked.connect(lambda checked=False, id=jid, name=jname: self._trigger_job_action(id, name, "stop"))
            if status != "RUNNING":
                btn_stop.setEnabled(False)

            btn_restart = QPushButton(" 🔃 ")
            btn_restart.setToolTip("Detiene y reinicia el job")
            btn_restart.setFixedSize(30, 26)
            btn_restart.setStyleSheet(style_btn)
            btn_restart.clicked.connect(lambda checked=False, id=jid, name=jname: self._trigger_job_action(id, name, "restart"))
            
            btn_log = QPushButton(" 📄 ")
            btn_log.setToolTip("Ver log en tiempo real")
            btn_log.setFixedSize(30, 26)
            btn_log.setStyleSheet(style_btn)
            btn_log.clicked.connect(lambda checked=False, id=jid, name=jname: self.show_log_viewer(id, name))
            
            lay.addWidget(btn_play)
            lay.addWidget(btn_stop)
            lay.addWidget(btn_restart)
            lay.addWidget(btn_log)
            self.table.setCellWidget(i, 7, container)

        self.card_total.set_value(str(len(jobs)))
        self.card_ok.set_value(str(total_ok))
        self.card_fail.set_value(str(total_fail))
        self.card_running.set_value(str(total_running))
        self.card_pend.set_value(str(total_pend))

        if current_id is not None:
            self._select_job_by_id(current_id)

    def show_log_viewer(self, job_id, job_name):
        dialog = LogDialog(job_id, job_name, self)
        dialog.show()

    def _auto_refresh(self):
        current_id = self._get_selected_id()
        self.load_jobs()
        if current_id:
            self._select_job_by_id(current_id)
            self.load_logs()

    def _get_selected_id(self):
        row = self.table.currentRow()
        if row == -1:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _get_job_name(self, job_id: int) -> str:
        rows = core.db_read("SELECT name FROM jobs WHERE id=?", (job_id,))
        return rows[0]["name"] if rows else str(job_id)

    def add_job(self):
        dialog = JobDialog(parent=self)
        if dialog.exec():
            name, command, labels, day, month, day_of_week, hour, minute, timeout_mins, max_instances, retries = dialog.get_data()
            core.db_write(
                "INSERT INTO jobs (name, command, labels, day, month, day_of_week, hour, minute, timeout_mins, max_instances, retries) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (name, command, labels, day, month, day_of_week, hour, minute, timeout_mins, max_instances, retries),
            )
            self.load_jobs()
            self.show_toast("✅ Job creado. El servicio acatará la orden en breve (máx. 15s)")

    def edit_job(self):
        job_id = self._get_selected_id()
        if job_id is None:
            return
        rows = core.db_read("SELECT * FROM jobs WHERE id=?", (job_id,))
        if not rows:
            return
        dialog = JobDialog(job=rows[0], parent=self)
        if dialog.exec():
            name, command, labels, day, month, day_of_week, hour, minute, timeout_mins, max_instances, retries = dialog.get_data()
            core.db_write(
                "UPDATE jobs SET name=?, command=?, labels=?, day=?, month=?, day_of_week=?, hour=?, minute=?, "
                "timeout_mins=?, max_instances=?, retries=? WHERE id=?",
                (name, command, labels, day, month, day_of_week, hour, minute, timeout_mins, max_instances, retries, job_id),
            )
            self.load_jobs()
            self.show_toast("✅ Job actualizado. El servicio acatará la orden en breve (máx. 15s)")

    def delete_job(self):
        job_id = self._get_selected_id()
        if job_id is None:
            return
        name = self._get_job_name(job_id)
        reply = QMessageBox.question(
            self, "Eliminar job",
            f"¿Eliminar «{name}» y todos sus logs?\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        core.db_write("DELETE FROM logs WHERE job_id=?", (job_id,))
        core.db_write("DELETE FROM jobs WHERE id=?", (job_id,))
        core.remove_scheduled_job(job_id)
        self.logs.clear()
        self.log_job_name.setText("")
        self.load_jobs()

    def _trigger_job_action(self, job_id, job_name, action):
        if action == "start":
            rows = core.db_read("SELECT status FROM logs WHERE job_id = ? ORDER BY id DESC LIMIT 1", (job_id,))
            if rows and rows[0]["status"] == "RUNNING":
                self.show_toast(f"ℹ️ El job '{job_name}' ya se está ejecutando.")
                return
                
            core.db_write("UPDATE jobs SET trigger_start = 1 WHERE id=?", (job_id,))
            self.show_toast(f"▶ {job_name} se iniciará en breve en 2do plano.")
        elif action == "stop":
            core.db_write("UPDATE jobs SET trigger_stop = 1 WHERE id=?", (job_id,))
            self.show_toast(f"⏹ Deteniendo {job_name} si estaba en ejecución.")
        elif action == "restart":
            core.db_write("UPDATE jobs SET trigger_stop = 1, trigger_start = 1 WHERE id=?", (job_id,))
            self.show_toast(f"🔃 {job_name} deteniéndose e iniciándose de nuevo...")
        
        QTimer.singleShot(2000, self.load_jobs)

    def show_toast(self, message):
        toast = QLabel(message, self)
        toast.setAlignment(Qt.AlignCenter)
        toast.setStyleSheet(f"""
            background-color: {C['surface2']};
            color: {C['text']};
            border: 1px solid {C['border']};
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 13px;
        """)
        toast.adjustSize()
        toast.move((self.width() - toast.width()) // 2, 80)
        toast.show()
        toast.raise_()
        
        QTimer.singleShot(3000, toast.deleteLater)

    def clear_logs(self):
        job_id = self._get_selected_id()
        if job_id is None:
            return
        reply = QMessageBox.question(
            self, "Limpiar logs",
            "¿Eliminar todos los logs de este job?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            core.db_write("DELETE FROM logs WHERE job_id=?", (job_id,))
            self.logs.clear()
            self.load_jobs()

    def load_logs(self):
        job_id = self._get_selected_id()
        if job_id is None:
            self.logs.clear()
            self.log_job_name.setText("")
            return

        self.log_job_name.setText(f"— {self._get_job_name(job_id)}")

        rows = [dict(row) for row in core.db_read("""
            SELECT output, error, status, created_at
            FROM logs
            WHERE job_id = ?
            ORDER BY id DESC
            LIMIT 20
        """, (job_id,))]

        self._last_log_rows = rows
        self.btn_log_details.setEnabled(bool(rows))

        if not rows:
            self.logs.setText("Sin ejecuciones registradas para este job.")
            return

        lines = []
        for row in rows:
            ts     = row["created_at"][:19].replace("T", " ")
            status = row["status"]
            out    = (row["output"] or "").strip().splitlines()[0] if row["output"] else ""
            err    = (row["error"]  or "").strip()
            if status == "OK":      marker = "✓"
            elif status == "RUNNING": marker = "⏳"
            else:                   marker = "✗"
            summary = f"{marker}  [{ts}]  {status}"
            details = []
            if out:
                details.append(f"stdout: {out}")
            if err:
                details.append("stderr")
            if details:
                summary += f" ({', '.join(details)})"
            lines.append(summary)

        self.logs.setText("\n".join(lines))


    def _show_log_details(self):
        if not self._last_log_rows:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalles de {self.log_job_name.text()[2:]}")
        dialog.setMinimumSize(700, 420)

        layout = QVBoxLayout(dialog)
        details = QTextEdit()
        details.setReadOnly(True)
        details.setStyleSheet(f"""
            QTextEdit {{
                background-color: {C['log_bg']};
                color: {C['log_text']};
                border: 1.5px solid {C['border']};
                border-radius: 10px;
                padding: 12px 16px;
                font-family: 'Cascadia Code', 'Consolas', 'Menlo', monospace;
                font-size: 12px;
            }}
        """)

        lines = []
        sep = "─" * 66
        for row in self._last_log_rows:
            ts     = row["created_at"][:19].replace("T", " ")
            status = row["status"]
            out    = (row["output"] or "").strip()
            err    = (row["error"]  or "").strip()
            if status == "OK":      marker = "✓"
            elif status == "RUNNING": marker = "⏳"
            else:                   marker = "✗"
            lines.append(sep)
            lines.append(f"{marker}  [{ts}]  STATUS: {status}")
            if out:
                lines.append(f"\nSTDOUT:\n{out}")
            if err:
                lines.append(f"\nSTDERR:\n{err}")
            lines.append("")

        details.setText("\n".join(lines))
        layout.addWidget(details)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dialog.accept)
        btn_close.setFixedHeight(30)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['surface']};
                color: {C['text']};
                border: 1.5px solid {C['border']};
                border-radius: 8px;
                padding: 0 18px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {C['bg']}; }}
        """)
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(btn_close)
        layout.addLayout(footer)

        dialog.exec()

    def closeEvent(self, event):
        self._timer.stop()
        core.shutdown_scheduler()
        event.accept()

if __name__ == "__main__":
    core.init_db()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path("cronvault.ico")))

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(C["bg"]))
    palette.setColor(QPalette.WindowText,      QColor(C["text"]))
    palette.setColor(QPalette.Base,            QColor(C["surface"]))
    palette.setColor(QPalette.AlternateBase,   QColor(C["surface2"]))
    palette.setColor(QPalette.Highlight,       QColor(C["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = App()
    window.setWindowIcon(QIcon(get_resource_path("cronvault.ico")))
    window.show()
    sys.exit(app.exec())