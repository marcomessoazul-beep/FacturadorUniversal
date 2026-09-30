import sys, os, json, re
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QTabWidget,
    QFormLayout, QLineEdit, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QTextEdit, QProgressBar, QGroupBox, QSplitter, QInputDialog
)

from database import Database
from ocr_engine import analyze_ticket
from learning_engine import LearningEngine
from validator import validate, FIELD_NAMES
from browser_engine import BrowserEngine

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "datos"
DOWNLOADS_DIR = DATA_DIR / "facturas"
DATA_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)


def bundled_tesseract_path():
    """Find bundled Tesseract when running from a PyInstaller build."""
    candidates = []
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append(base / "vendor" / "tesseract" / "tesseract.exe")
        candidates.append(Path(sys.executable).parent / "vendor" / "tesseract" / "tesseract.exe")
    candidates.extend([
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ])
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""

FIELDS = ["rfc","razon_social","cp","regimen_fiscal","uso_cfdi","correo",
          "ticket","fecha","hora","total","tc","tr","itu","sucursal"]

class AutomationThread(QThread):
    ready = Signal(object)
    submitted = Signal(object)
    downloads = Signal(object)
    failed = Signal(str)

    def __init__(self, portal_url, data, learner):
        super().__init__()
        self.portal_url = portal_url
        self.data = data
        self.learner = learner
        self.session = None
        self._mappings = {}

    def run(self):
        try:
            engine = BrowserEngine()
            self.session = engine.start(
                self.portal_url, self.data, self.learner, DOWNLOADS_DIR,
                callback=self.callback
            )
            self.session.open_and_fill()
        except Exception as e:
            self.failed.emit(str(e))

    def callback(self, payload):
        kind = payload.get("type")
        if kind == "ready":
            self.ready.emit(payload)
        elif kind == "submitted":
            self.submitted.emit(payload)
        elif kind == "downloads":
            self.downloads.emit(payload)

    def continue_process(self, mappings=None):
        self._mappings = mappings or {}
        if self.session:
            self.session.continue_now(self._mappings)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Facturador Universal")
        self.resize(1200, 780)

        self.db = Database()
        self.learner = LearningEngine(self.db)
        self.current_analysis = None
        self.current_ticket_id = None

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_tickets_tab()
        self._build_assist_tab()
        self._build_learning_tab()
        self._build_history_tab()
        self._build_settings_tab()

        self.refresh_learning()

    def _build_tickets_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        header = QLabel("Facturador Universal")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Sube un ticket. El sistema encuentra el portal, extrae datos y automatiza el llenado.")
        subtitle.setStyleSheet("color:#666;")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        row = QHBoxLayout()
        self.btn_add = QPushButton("📸 Agregar ticket")
        self.btn_read = QPushButton("🔎 Leer ticket")
        self.btn_automate = QPushButton("▶ Automatizar")
        self.btn_add.clicked.connect(self.add_ticket)
        self.btn_read.clicked.connect(self.read_selected)
        self.btn_automate.clicked.connect(self.start_automation)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_read)
        row.addWidget(self.btn_automate)
        row.addStretch()
        layout.addLayout(row)

        self.ticket_list = QListWidget()
        layout.addWidget(self.ticket_list)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget(); ll = QVBoxLayout(left)
        self.preview = QLabel("Vista previa")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(360, 320)
        self.preview.setStyleSheet("border:1px solid #ddd; background:#fafafa;")
        ll.addWidget(self.preview)
        splitter.addWidget(left)

        right = QWidget(); rl = QVBoxLayout(right)
        self.status_label = QLabel("Estado: listo")
        rl.addWidget(self.status_label)
        self.portal_input = QLineEdit()
        self.portal_input.setPlaceholderText("URL del portal (se detecta desde QR/URL del ticket si existe)")
        rl.addWidget(QLabel("Portal de facturación"))
        rl.addWidget(self.portal_input)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        rl.addWidget(QLabel("Texto detectado"))
        rl.addWidget(self.raw_text)

        self.data_table = QTableWidget(0, 3)
        self.data_table.setHorizontalHeaderLabels(["Dato", "Valor", "Estado"])
        self.data_table.horizontalHeader().setStretchLastSection(True)
        rl.addWidget(QLabel("Datos detectados"))
        rl.addWidget(self.data_table)

        splitter.addWidget(right)
        layout.addWidget(splitter)
        self.tabs.addTab(root, "Tickets")

    def _build_assist_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("Asistencia y aprendizaje")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
        self.assist_banner = QLabel("Sin sesión de navegador activa.")
        self.assist_banner.setStyleSheet("padding:8px; border:1px solid #ddd;")
        layout.addWidget(self.assist_banner)
        layout.addWidget(QLabel(
            "Cuando un campo no es seguro, selecciona qué dato representa. "
            "La corrección se guarda como ejemplo y el motor aprende para futuros portales."
        ))

        self.assist_table = QTableWidget(0, 4)
        self.assist_table.setHorizontalHeaderLabels(
            ["Campo del portal", "Predicción", "Confianza", "Asignar dato"]
        )
        self.assist_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.assist_table)

        row = QHBoxLayout()
        self.btn_save_learning = QPushButton("🧠 Guardar correcciones y aprender")
        self.btn_continue = QPushButton("▶ Continuar automatización")
        self.btn_save_learning.clicked.connect(self.save_learning)
        self.btn_continue.clicked.connect(self.continue_automation)
        row.addWidget(self.btn_save_learning)
        row.addWidget(self.btn_continue)
        row.addStretch()
        layout.addLayout(row)

        self.tabs.addTab(root, "Asistencia y aprendizaje")

    def _build_learning_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("Lo que el sistema ha aprendido")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
        self.learning_summary = QLabel()
        layout.addWidget(self.learning_summary)
        layout.addWidget(QLabel("Cada asistencia humana se guarda como ejemplo (campo del portal → dato correcto) y se usa para mejorar las predicciones futuras."))

        self.learning_table = QTableWidget(0, 4)
        self.learning_table.setHorizontalHeaderLabels(
            ["Ejemplo", "Dato aprendido", "Comercio", "Fecha"]
        )
        self.learning_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.learning_table)
        self.tabs.addTab(root, "Aprendizaje")

    def _build_history_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("Historial y errores")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        layout.addWidget(self.history_text)
        self.tabs.addTab(root, "Historial")

    def _build_settings_tab(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        fiscal = QGroupBox("Perfil fiscal")
        form = QFormLayout(fiscal)
        self.settings = {}
        labels = {
            "rfc":"RFC","razon_social":"Razón social","cp":"Código postal fiscal",
            "regimen_fiscal":"Régimen fiscal","uso_cfdi":"Uso de CFDI","correo":"Correo"
        }
        for key, label in labels.items():
            edit = QLineEdit(self.db.get(key, ""))
            self.settings[key] = edit
            form.addRow(label, edit)
        btn = QPushButton("Guardar perfil fiscal")
        btn.clicked.connect(self.save_settings)
        form.addRow(btn)

        ocr_box = QGroupBox("OCR")
        of = QFormLayout(ocr_box)
        self.tess_path = QLineEdit(self.db.get("tesseract_cmd", bundled_tesseract_path()))
        browse = QPushButton("Buscar...")
        browse.clicked.connect(self.select_tesseract)
        r = QHBoxLayout(); r.addWidget(self.tess_path); r.addWidget(browse)
        w = QWidget(); w.setLayout(r)
        of.addRow("Ruta de tesseract.exe", w)

        layout.addWidget(fiscal)
        layout.addWidget(ocr_box)
        layout.addWidget(QLabel(
            "Consejo: configura tus datos fiscales antes de automatizar. "
            "El sistema no adivina ni modifica el Uso de CFDI por su cuenta."
        ))
        layout.addStretch()
        self.tabs.addTab(root, "Configuración")

    def add_ticket(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar tickets", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        for path in files:
            self.ticket_list.addItem(path)
        if files:
            self.ticket_list.setCurrentRow(self.ticket_list.count()-1)

    def read_selected(self):
        item = self.ticket_list.currentItem()
        if not item:
            QMessageBox.information(self, "Ticket", "Selecciona una foto primero.")
            return
        path = item.text()
        self.status_label.setText("Estado: leyendo QR y OCR...")
        QApplication.processEvents()
        analysis = analyze_ticket(path, self.db.get("tesseract_cmd", bundled_tesseract_path()))
        self.current_analysis = analysis
        self.preview.setPixmap(QPixmap(path).scaled(
            420, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        self.raw_text.setPlainText(analysis["raw_text"])
        self._show_data(analysis["data"])

        portal = analysis["qr_url"] or (analysis["urls"][0] if analysis["urls"] else "")
        if portal:
            analysis["portal_url"] = portal
        else:
            analysis["portal_url"] = ""
        issues = validate(analysis["data"])
        for code, msg, solution in issues:
            self.db.add_error(code, msg, solution, analysis["merchant"])
        self.status_label.setText(
            f"Estado: {analysis['merchant']} | Portal: {analysis.get('portal_url') or 'no detectado'} | "
            f"Alertas: {len(issues)}"
        )
        self.portal_input.setText(analysis.get("portal_url",""))
        self.prepare_assistance()

    def _show_data(self, data):
        self.data_table.setRowCount(0)
        for key in FIELDS:
            value = data.get(key, "")
            if value:
                row = self.data_table.rowCount()
                self.data_table.insertRow(row)
                self.data_table.setItem(row, 0, QTableWidgetItem(FIELD_NAMES.get(key, key)))
                self.data_table.setItem(row, 1, QTableWidgetItem(str(value)))
                issues = validate({key:value})
                self.data_table.setItem(row, 2, QTableWidgetItem("⚠ Revisar" if issues else "✓"))

    def prepare_assistance(self):
        self.assist_table.setRowCount(0)
        if not self.current_analysis:
            return
        portal = self.current_analysis.get("portal_url")
        if not portal:
            # Muestra un ejemplo de asistencia manual para que el flujo pueda empezar
            for key in ("ticket","fecha","total","tc","tr","itu"):
                row = self.assist_table.rowCount()
                self.assist_table.insertRow(row)
                self.assist_table.setItem(row, 0, QTableWidgetItem(f"Portal no detectado → usar {FIELD_NAMES[key]}"))
                self.assist_table.setItem(row, 1, QTableWidgetItem("—"))
                self.assist_table.setItem(row, 2, QTableWidgetItem("0%"))
                combo = QComboBox()
                combo.addItem("Seleccionar…","")
                for f in FIELDS:
                    combo.addItem(FIELD_NAMES[f], f)
                combo.setCurrentIndex(combo.findData(key))
                self.assist_table.setCellWidget(row, 3, combo)
            return
        # En un portal real esta tabla se llena después de inspeccionar la página.
        # Por ahora mostramos los campos más relevantes que el usuario podrá enseñar.
        descriptors = [
            "input name=ticket placeholder=Ticket",
            "input name=folio placeholder=Folio",
            "input name=rfc placeholder=RFC",
            "input name=cp placeholder=Código postal",
            "select name=uso_cfdi aria=Uso de CFDI",
            "input name=total placeholder=Total",
        ]
        for desc in descriptors:
            target, conf = self.learner.predict(desc)
            row = self.assist_table.rowCount()
            self.assist_table.insertRow(row)
            self.assist_table.setItem(row,0,QTableWidgetItem(desc))
            self.assist_table.setItem(row,1,QTableWidgetItem(FIELD_NAMES.get(target,target or "Sin predicción")))
            self.assist_table.setItem(row,2,QTableWidgetItem(f"{conf*100:.0f}%"))
            combo=QComboBox()
            combo.addItem("Seleccionar…","")
            for f in FIELDS:
                combo.addItem(FIELD_NAMES[f], f)
            if target:
                combo.setCurrentIndex(combo.findData(target))
            self.assist_table.setCellWidget(row,3,combo)

    def save_learning(self):
        if not self.current_analysis:
            QMessageBox.information(self, "Aprendizaje", "Carga y lee un ticket primero.")
            return
        merchant = self.current_analysis.get("merchant","")
        for row in range(self.assist_table.rowCount()):
            descriptor_item = self.assist_table.item(row,0)
            combo = self.assist_table.cellWidget(row,3)
            if not descriptor_item or not combo:
                continue
            target = combo.currentData()
            if target:
                self.learner.learn(descriptor_item.text(), target, merchant)
        self.refresh_learning()
        QMessageBox.information(
            self, "Aprendizaje guardado",
            "Las correcciones fueron guardadas. En próximos portales el sistema podrá reutilizarlas."
        )

    def start_automation(self):
        if not self.current_analysis:
            QMessageBox.information(self, "Automatizar", "Primero carga y lee un ticket.")
            return

        data = dict(self.current_analysis.get("data",{}))
        # Merge fiscal profile.
        for key, edit in self.settings.items():
            if edit.text().strip():
                data[key] = edit.text().strip()

        issues = validate(data)
        if issues:
            msg = "\n\n".join(f"{c}: {m}\nSolución: {s}" for c,m,s in issues)
            QMessageBox.warning(self, "No se puede automatizar todavía", msg)
            return

        portal = self.portal_input.text().strip() or self.current_analysis.get("portal_url","").strip()
        if not portal:
            portal, ok = QInputDialog.getText(
                self,
                "Portal de facturación",
                "No se encontró la página en el ticket. Pega la URL del portal:"
            )
            if not ok or not portal.strip():
                return
            portal = portal.strip()
        self.current_analysis["portal_url"] = portal
        self.status_label.setText("Estado: abriendo navegador y buscando campos...")
        self.thread = AutomationThread(portal, data, self.learner)
        self.thread.ready.connect(self.browser_ready)
        self.thread.submitted.connect(self.browser_submitted)
        self.thread.downloads.connect(self.browser_downloads)
        self.thread.failed.connect(self.automation_failed)
        self.thread.start()

    def browser_ready(self, payload):
        fields = payload.get("fields", [])
        self.assist_table.setRowCount(0)
        for f in fields:
            row = self.assist_table.rowCount()
            self.assist_table.insertRow(row)
            self.assist_table.setItem(row,0,QTableWidgetItem(f["descriptor"]))
            self.assist_table.setItem(row,1,QTableWidgetItem(FIELD_NAMES.get(f["target_field"],f["target_field"] or "Sin predicción")))
            self.assist_table.setItem(row,2,QTableWidgetItem(f'{f["confidence"]*100:.0f}%'))
            combo=QComboBox()
            combo.addItem("No usar","")
            for k in FIELDS:
                combo.addItem(FIELD_NAMES[k], k)
            if f["target_field"]:
                combo.setCurrentIndex(combo.findData(f["target_field"]))
            self.assist_table.setCellWidget(row,3,combo)
        extra = " CAPTCHA detectado: resuélvelo en el navegador." if payload.get("captcha") else ""
        self.status_label.setText(
            f"Estado: navegador abierto | {len(fields)} campos detectados | "
            f"Campos inciertos: {payload.get('uncertain_count',0)}.{extra}"
        )
        self.tabs.setCurrentIndex(1)

    def browser_submitted(self, payload):
        self.status_label.setText(
            "Estado: se intentó ejecutar la acción de facturación" +
            (f" ({payload.get('clicked')})" if payload.get('clicked') else " (no se identificó un botón seguro)")
        )

    def browser_downloads(self, payload):
        self.status_label.setText(
            f"Estado: {payload.get('message','Proceso terminado.')} "
            f"PDF: {payload.get('pdf') or '—'} | XML: {payload.get('xml') or '—'}"
        )


    def continue_automation(self):
        if not hasattr(self, "thread") or not self.thread.isRunning():
            QMessageBox.information(self, "Automatización", "No hay una sesión activa.")
            return
        mappings = {}
        for row in range(self.assist_table.rowCount()):
            combo = self.assist_table.cellWidget(row, 3)
            if combo:
                target = combo.currentData()
                if target:
                    mappings[str(row)] = target
        self.thread.continue_process(mappings)

    def automation_failed(self, error):
        self.status_label.setText("Estado: error")
        QMessageBox.critical(
            self, "Error durante la automatización",
            f"{error}\n\nSolución sugerida:\n"
            "1) Revisa la conexión.\n"
            "2) Abre el portal manualmente y confirma que siga disponible.\n"
            "3) Guarda una nueva corrección de campos.\n"
            "4) Si aparece CAPTCHA/MFA, resuélvelo manualmente."
        )

    def refresh_learning(self):
        stats = self.learner.stats()
        by_field = ", ".join(f"{FIELD_NAMES.get(k,k)}: {v}" for k,v in stats["by_field"].items())
        self.learning_summary.setText(
            f"Ejemplos aprendidos: {stats['examples']} | {by_field or 'aún no hay ejemplos'}"
        )
        rows = self.db.get_learning()
        self.learning_table.setRowCount(0)
        for r in rows:
            row = self.learning_table.rowCount()
            self.learning_table.insertRow(row)
            self.learning_table.setItem(row,0,QTableWidgetItem(r["descriptor"]))
            self.learning_table.setItem(row,1,QTableWidgetItem(FIELD_NAMES.get(r["target_field"],r["target_field"])))
            self.learning_table.setItem(row,2,QTableWidgetItem(r["merchant"] or "—"))
            self.learning_table.setItem(row,3,QTableWidgetItem(r["created_at"]))

    def save_settings(self):
        for key, edit in self.settings.items():
            self.db.set(key, edit.text().strip())
        self.db.set("tesseract_cmd", self.tess_path.text().strip())
        QMessageBox.information(self, "Guardado", "Perfil fiscal y configuración guardados.")

    def select_tesseract(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar tesseract.exe", "", "Ejecutable (*.exe)")
        if path:
            self.tess_path.setText(path)

    def closeEvent(self, event):
        self.db.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
