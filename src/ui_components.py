import hashlib
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QLabel, QDialog, QFormLayout, QSpinBox, QFrame, QMessageBox, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt
C = {
    "bg":            "#f1f5f9",
    "surface":       "#ffffff",
    "surface2":      "#f8fafc",
    "border":        "#e2e8f0",
    "accent":        "#6366f1",
    "accent_hover":  "#4f46e5",
    "accent_light":  "#eef2ff",
    "danger":        "#ef4444",
    "danger_light":  "#fef2f2",
    "success":       "#22c55e",
    "success_light": "#f0fdf4",
    "warn":          "#f59e0b",
    "warn_light":    "#fffbeb",
    "text":          "#0f172a",
    "text_secondary":"#64748b",
    "text_muted":    "#94a3b8",
    "log_bg":        "#0f172a",
    "log_text":      "#a3e635",
}

CHIP_COLORS = [
    ("#6366f1", "#eef2ff"),
    ("#0ea5e9", "#f0f9ff"),
    ("#10b981", "#ecfdf5"),
    ("#f59e0b", "#fffbeb"),
    ("#ec4899", "#fdf2f8"),
    ("#8b5cf6", "#f5f3ff"),
    ("#14b8a6", "#f0fdfa"),
    ("#f97316", "#fff7ed"),
]

def label_color(label: str) -> tuple:
    idx = int(hashlib.md5(label.encode()).hexdigest(), 16) % len(CHIP_COLORS)
    return CHIP_COLORS[idx]

class LabelChip(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(f"  {text}  ", parent)
        fg, bg = label_color(text)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 9px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 0px;
            }}
        """)
        self.setFixedHeight(20)

class ChipsWidget(QWidget):
    def __init__(self, labels: list, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for lbl in labels[:4]:
            layout.addWidget(LabelChip(lbl.strip()))
        layout.addStretch()

class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", accent: str = "#6366f1", parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C['surface']};
                border-radius: 12px;
                border: 1.5px solid {C['border']};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(
            f"color:{C['text_muted']};font-size:10px;font-weight:600;"
            f"letter-spacing:0.8px;border:none;background:transparent;"
        )
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(
            f"color:{accent};font-size:24px;font-weight:700;"
            f"border:none;background:transparent;"
        )
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_value(self, v: str):
        self.lbl_value.setText(v)

class JobDialog(QDialog):
    def __init__(self, job=None, parent=None):
        super().__init__(parent)
        if job and not isinstance(job, dict):
            job = dict(job)
        self.setWindowTitle("Editar trabajo" if job else "Nuevo trabajo")
        self.setMinimumWidth(560)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(28, 24, 28, 24)

        title_lbl = QLabel("Editar trabajo" if job else "Nuevo trabajo")
        title_lbl.setStyleSheet(
            f"font-size:17px;font-weight:700;color:{C['text']};"
            f"background:transparent;border:none;"
        )
        root.addWidget(title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color:{C['border']};max-height:1px;border:none;")
        root.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        def mk_label(text):
            l = QLabel(text)
            l.setStyleSheet(
                f"color:{C['text_secondary']};font-size:13px;"
                f"font-weight:500;background:transparent;border:none;"
            )
            return l

        field_style = f"""
            QLineEdit, QSpinBox {{
                background-color: {C['bg']};
                color: {C['text']};
                border: 1.5px solid {C['border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border-color: {C['accent']};
                background-color: {C['surface']};
            }}
        """

        self.name = QLineEdit()
        self.name.setPlaceholderText("Nombre descriptivo del job")
        self.name.setStyleSheet(field_style)

        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(6)
        self.command = QLineEdit()
        self.command.setPlaceholderText("comando libre  o  ruta a .bat / .sh / .py …")
        self.command.setStyleSheet(field_style)
        btn_browse = QPushButton("📂")
        btn_browse.setFixedSize(32, 32)
        btn_browse.setToolTip("Elegir archivo ejecutable")
        btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['bg']};
                border: 1.5px solid {C['border']};
                border-radius: 8px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {C['accent_light']}; border-color: {C['accent']}; }}
        """)
        btn_browse.clicked.connect(self._browse_file)
        cmd_row.addWidget(self.command)
        cmd_row.addWidget(btn_browse)

        self.labels = QLineEdit()
        self.labels.setPlaceholderText("backup, sync, db  (separados por coma)")
        self.labels.setStyleSheet(field_style)

        self.schedule = QComboBox()
        self.schedule.addItems([
            "Diario",
            "Personalizado"
        ])
        self.schedule.setStyleSheet(field_style)
        
        schedule_custom_layout = QVBoxLayout()
        schedule_custom_layout.setSpacing(4)
        schedule_custom_layout.setContentsMargins(0, 0, 0, 0)
        
        schedule_custom_label = QLabel("Ingresa números de días separados por coma (1=Lunes, 2=Martes... 7=Domingo)")
        schedule_custom_label.setStyleSheet(f"color:{C['text_muted']};font-size:11px;background:transparent;border:none;")
        
        self.schedule_custom = QLineEdit()
        self.schedule_custom.setPlaceholderText("ej. 1,3,4,6")
        self.schedule_custom.setStyleSheet(field_style)
        
        schedule_custom_layout.addWidget(schedule_custom_label)
        schedule_custom_layout.addWidget(self.schedule_custom)
        
        self.schedule_custom_container = QWidget()
        self.schedule_custom_container.setLayout(schedule_custom_layout)
        self.schedule_custom_container.setVisible(False)
        self.schedule_custom_label = schedule_custom_label
        
        self.schedule.currentTextChanged.connect(self._on_schedule_changed)

        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        self.hour   = QSpinBox(); self.hour.setRange(0, 23);  self.hour.setSuffix(" h")
        self.minute = QSpinBox(); self.minute.setRange(0, 59); self.minute.setSuffix(" m")
        for sp in (self.hour, self.minute):
            sp.setStyleSheet(field_style)
            sp.setFixedWidth(80)
        colon = QLabel(":")
        colon.setStyleSheet(f"color:{C['text_secondary']};font-size:16px;background:transparent;border:none;")
        time_row.addWidget(self.hour)
        time_row.addWidget(colon)
        time_row.addWidget(self.minute)
        time_row.addStretch()

        adv_row = QHBoxLayout()
        adv_row.setSpacing(12)
        
        self.timeout_mins = QSpinBox()
        self.timeout_mins.setRange(1, 1440)
        self.timeout_mins.setValue(20)
        self.timeout_mins.setSuffix(" min")
        self.timeout_mins.setFixedWidth(80)
        self.timeout_mins.setStyleSheet(field_style)
        
        self.max_instances = QSpinBox()
        self.max_instances.setRange(1, 5)
        self.max_instances.setValue(1)
        self.max_instances.setFixedWidth(60)
        self.max_instances.setStyleSheet(field_style)
        
        self.retries = QSpinBox()
        self.retries.setRange(0, 10)
        self.retries.setValue(2)
        self.retries.setFixedWidth(60)
        self.retries.setStyleSheet(field_style)
        
        adv_row.addWidget(mk_label("Timeout:"))
        adv_row.addWidget(self.timeout_mins)
        adv_row.addWidget(mk_label("Concurrencia:"))
        adv_row.addWidget(self.max_instances)
        adv_row.addWidget(mk_label("Reintentos:"))
        adv_row.addWidget(self.retries)
        adv_row.addStretch()

        if job:
            self.name.setText(job["name"])
            self.command.setText(job["command"])
            self.labels.setText(job["labels"])
            self._load_schedule_from_job(job)
            self.hour.setValue(job["hour"])
            self.minute.setValue(job["minute"])
            self.timeout_mins.setValue(job.get("timeout_mins", 20))
            self.max_instances.setValue(job.get("max_instances", 1))
            self.retries.setValue(job.get("retries", 2))

        form.addRow(mk_label("Nombre *"),           self.name)
        form.addRow(mk_label("Comando *"),          cmd_row)
        form.addRow(mk_label("Programación"),       self.schedule)
        form.addRow(mk_label(""),                   self.schedule_custom_container)
        form.addRow(mk_label("Hora / Minuto"),      time_row)
        form.addRow(mk_label("Avanzado"),           adv_row)
        form.addRow(mk_label("Labels"),             self.labels)
        root.addLayout(form)

        root.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['surface']};
                color: {C['text_secondary']};
                border: 1.5px solid {C['border']};
                border-radius: 8px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {C['bg']}; }}
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Guardar")
        btn_save.setFixedHeight(36)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {C['accent_hover']}; }}
        """)
        btn_save.clicked.connect(self._validate_and_accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

        self.setStyleSheet(f"QDialog {{ background-color: {C['surface']}; }}")

    def _on_schedule_changed(self, text):
        """Mostrar/ocultar campo personalizado según la opción seleccionada."""
        is_custom = text == "Personalizado"
        self.schedule_custom_container.setVisible(is_custom)

    def _schedule_to_cron(self, schedule_type: str) -> tuple:
        """Convierte el tipo de schedule a valores cron (day, month, day_of_week)."""
        schedules = {
            "Diario": ("*", "*", "*"),
            "Personalizado": ("*", "*", "*"),
        }
        return schedules.get(schedule_type, ("*", "*", "*"))

    def _cron_to_schedule(self, day: str, month: str, day_of_week: str) -> str:
        """Intenta mapear valores cron a un schedule predefinido."""
        if day == "*" and month == "*" and day_of_week == "*":
            return "Diario"
        return "Personalizado"

    def _load_schedule_from_job(self, job):
        """Carga la programación desde un job existente."""
        if not isinstance(job, dict):
            job = dict(job)
        day = job.get("day", "*")
        month = job.get("month", "*")
        day_of_week = job.get("day_of_week", "*")
        
        schedule_type = self._cron_to_schedule(day, month, day_of_week)
        idx = self.schedule.findText(schedule_type)
        if idx >= 0:
            self.schedule.setCurrentIndex(idx)
        else:
            self.schedule.setCurrentText("Personalizado")
        
        if schedule_type == "Personalizado":
            self.schedule_custom.setText(day_of_week)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo ejecutable",
            str(Path.home()),
            "Ejecutables (*.bat *.sh *.py *.exe *.cmd *.ps1);;Todos los archivos (*)"
        )
        if path:
            self.command.setText(path)

    def _validate_and_accept(self):
        errors = []
        if not self.name.text().strip():
            errors.append("• El nombre no puede estar vacío.")
        if not self.command.text().strip():
            errors.append("• El comando no puede estar vacío.")
        if errors:
            QMessageBox.warning(self, "Campos requeridos", "\n".join(errors))
            return
        self.accept()

    def get_data(self) -> tuple:
        clean_labels = ",".join(
            l.strip() for l in self.labels.text().split(",") if l.strip()
        )
        
        schedule_text = self.schedule.currentText()
        
        if schedule_text == "Personalizado":
            day_of_week = self.schedule_custom.text().strip() or "*"
        else:
            day_of_week = "*"
        
        return (
            self.name.text().strip(),
            self.command.text().strip(),
            clean_labels,
            "*",
            "*",
            day_of_week,
            self.hour.value(),
            self.minute.value(),
            self.timeout_mins.value(),
            self.max_instances.value(),
            self.retries.value()
        )