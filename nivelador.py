#!/usr/bin/env python3
"""Nivelador de volumen by tuxor - GUI para mp3gain"""

import sys
import os
import subprocess
import re
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QCheckBox, QRadioButton, QLabel, QScrollArea,
    QPushButton, QProgressBar, QTextEdit, QSpinBox, QDoubleSpinBox,
    QFrame, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QComboBox, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QPalette, QColor

VERSION = "v1.0"
REVISION = "Rev 1"
FECHA_REV = "2026-03-25"

STYLE = """
QMainWindow { background-color: #1e1e1e; }

QGroupBox {
    font-weight: bold;
    font-size: 14px;
    border: 1px solid #555;
    border-radius: 8px;
    margin-top: 16px;
    padding: 20px 12px 12px 12px;
    color: #4fc3f7;
    background-color: #262626;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    background-color: #262626;
}

QLabel { color: #eee; font-size: 13px; }

QCheckBox, QRadioButton {
    color: #eee;
    spacing: 8px;
    font-size: 13px;
    padding: 3px 0;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px; height: 18px;
}
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
    border: 2px solid #888;
    background-color: #333;
    border-radius: 3px;
}
QCheckBox::indicator:checked {
    border: 2px solid #4fc3f7;
    background-color: #4fc3f7;
    border-radius: 3px;
}
QRadioButton::indicator:unchecked {
    border-radius: 9px;
}
QRadioButton::indicator:checked {
    border: 2px solid #4fc3f7;
    background-color: #4fc3f7;
    border-radius: 9px;
}

QPushButton {
    background-color: #3a3a3a;
    color: #eee;
    border: 1px solid #666;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover { background-color: #4a4a4a; border-color: #4fc3f7; }
QPushButton:disabled { background-color: #2a2a2a; color: #555; border-color: #3a3a3a; }

QProgressBar {
    border: 1px solid #444;
    border-radius: 6px;
    text-align: center;
    color: white;
    font-weight: bold;
    font-size: 12px;
    background-color: #2a2a2a;
    min-height: 26px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1565c0, stop:1 #42a5f5);
    border-radius: 5px;
}

QTextEdit {
    background-color: #1a1a1a;
    color: #aed581;
    border: 1px solid #444;
    border-radius: 6px;
    font-family: 'Consolas', 'DejaVu Sans Mono', monospace;
    font-size: 12px;
    padding: 6px;
}

QTreeWidget {
    background-color: #1e1e1e;
    alternate-background-color: #262626;
    border: 1px solid #444;
    border-radius: 6px;
    color: #eee;
    font-size: 14px;
}
QTreeWidget::item {
    padding: 4px 0;
    background-color: #1e1e1e;
}
QTreeWidget::item:alternate {
    background-color: #262626;
}
QTreeWidget::item:selected { background-color: #1565c0; }

QHeaderView::section {
    background-color: #2a2a2a;
    color: #4fc3f7;
    border: 1px solid #444;
    padding: 6px 10px;
    font-weight: bold;
    font-size: 13px;
}

QSpinBox, QDoubleSpinBox {
    background-color: #333;
    color: #eee;
    border: 1px solid #666;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 13px;
    min-height: 26px;
}

QComboBox {
    background-color: #333;
    color: #eee;
    border: 1px solid #666;
    border-radius: 4px;
    padding: 4px 6px;
    font-size: 13px;
    min-height: 26px;
}
QComboBox::drop-down { border: none; width: 20px; }

QScrollArea { border: none; background-color: #1e1e1e; }
QScrollArea > QWidget > QWidget { background-color: #1e1e1e; }

QToolTip {
    background-color: #333;
    color: #eee;
    border: 1px solid #4fc3f7;
    border-radius: 4px;
    padding: 8px;
    font-size: 14px;
}

QStatusBar { color: #999; font-size: 12px; }
"""


def format_size(size_bytes):
    """Formatea bytes a unidad legible"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def find_mp3_files(folder):
    """Busca archivos MP3 recursivamente"""
    mp3_files = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for f in sorted(files):
            if f.lower().endswith('.mp3'):
                mp3_files.append(os.path.join(root, f))
    return mp3_files


class Mp3GainWorker(QThread):
    """Hilo para ejecutar mp3gain sin bloquear la interfaz"""
    progress = pyqtSignal(int, int, str)  # current, total, filename
    file_result = pyqtSignal(str, str)    # filepath, gain_info
    log_message = pyqtSignal(str)
    finished_work = pyqtSignal(bool, str) # success, message

    def __init__(self, files, args, mode="analyze"):
        super().__init__()
        self.files = files
        self.args = args
        self.mode = mode
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        total = len(self.files)
        if total == 0:
            self.finished_work.emit(False, "No hay archivos para procesar")
            return

        if self.mode == "album":
            self._run_album(total)
        else:
            self._run_per_file(total)

    def _run_per_file(self, total):
        processed = 0
        for i, filepath in enumerate(self.files):
            if self._stop:
                self.finished_work.emit(False, f"Detenido. {processed}/{total} archivos procesados.")
                return

            filename = os.path.basename(filepath)
            self.progress.emit(i + 1, total, filename)

            cmd = ["mp3gain"] + self.args + [filepath]
            self.log_message.emit(f"Ejecutando: mp3gain {' '.join(self.args)} \"{filename}\"")

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                output = result.stdout + result.stderr
                gain_info = self._parse_gain(output, filepath)
                self.file_result.emit(filepath, gain_info)
                if output.strip():
                    for line in output.strip().split('\n'):
                        line = line.strip()
                        if line:
                            self.log_message.emit(f"  {line}")
                processed += 1
            except subprocess.TimeoutExpired:
                self.log_message.emit(f"  TIMEOUT: {filename}")
                self.file_result.emit(filepath, "Error: timeout")
            except Exception as e:
                self.log_message.emit(f"  ERROR: {e}")
                self.file_result.emit(filepath, f"Error: {e}")

        self.finished_work.emit(True, f"Completado: {processed}/{total} archivos procesados.")

    def _run_album(self, total):
        self.progress.emit(1, 1, "Procesando album completo...")
        self.log_message.emit(f"Procesando {total} archivos como album...")

        cmd = ["mp3gain"] + self.args + self.files
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            output = result.stdout + result.stderr
            if output.strip():
                for line in output.strip().split('\n'):
                    line = line.strip()
                    if line:
                        self.log_message.emit(f"  {line}")

            # Parsear resultados por archivo
            for filepath in self.files:
                gain_info = self._parse_gain(output, filepath)
                self.file_result.emit(filepath, gain_info)

            self.progress.emit(1, 1, "Completado")
            self.finished_work.emit(True, f"Album procesado: {total} archivos.")
        except subprocess.TimeoutExpired:
            self.log_message.emit("TIMEOUT procesando album")
            self.finished_work.emit(False, "Timeout procesando album")
        except Exception as e:
            self.log_message.emit(f"ERROR: {e}")
            self.finished_work.emit(False, str(e))

    def _parse_gain(self, output, filepath):
        """Intenta extraer la ganancia recomendada de la salida de mp3gain"""
        filename = os.path.basename(filepath)
        for line in output.split('\n'):
            if filename in line or filepath in line:
                # Buscar patron "dB change" o "Recommended"
                match = re.search(r'([-+]?\d+\.?\d*)\s*dB', line)
                if match:
                    return f"{match.group(1)} dB"
        # Buscar en formato tabulado
        for line in output.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3:
                for part in parts:
                    if filename in part or filepath in part:
                        for p in parts:
                            match = re.search(r'([-+]?\d+\.?\d*)', p)
                            if match and p != part:
                                return f"{match.group(1)} dB"
        return "OK"


class DropZone(QFrame):
    folder_dropped = None  # Se asigna desde la ventana principal

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        self.setMaximumHeight(130)
        self.setStyleSheet("""
            DropZone {
                border: 3px dashed #888;
                border-radius: 12px;
                background-color: #2b2b2b;
            }
            DropZone:hover {
                border-color: #4fc3f7;
                background-color: #1e3a4a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(2)

        icon_label = QLabel("\U0001F4C2")
        icon_label.setFont(QFont("", 30))
        icon_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel("Arrastra una carpeta aqui")
        text_label.setFont(QFont("", 14, QFont.Bold))
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("color: #ccc; border: none; background: transparent;")

        sub_label = QLabel("Se buscaran archivos MP3 recursivamente")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("color: #999; border: none; background: transparent;")

        self.btn_browse = QPushButton("O selecciona una carpeta...")
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a; color: #eee;
                border: 1px solid #777; border-radius: 6px;
                padding: 6px 20px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #5a5a5a; border-color: #4fc3f7; }
        """)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addWidget(sub_label)
        layout.addWidget(self.btn_browse, alignment=Qt.AlignCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and os.path.isdir(urls[0].toLocalFile()):
                event.acceptProposedAction()
                self.setStyleSheet("""
                    DropZone {
                        border: 3px dashed #4fc3f7;
                        border-radius: 12px;
                        background-color: #1e3a4a;
                    }
                """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropZone {
                border: 3px dashed #888;
                border-radius: 12px;
                background-color: #2b2b2b;
            }
            DropZone:hover {
                border-color: #4fc3f7;
                background-color: #1e3a4a;
            }
        """)

    def dropEvent(self, event):
        self.dragLeaveEvent(event)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path) and self.folder_dropped:
                self.folder_dropped(path)


class NiveladorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Nivelador de volumen by tuxor {VERSION}")
        self.setMinimumSize(1050, 780)
        self.resize(1100, 850)
        self.mp3_files = []        # Lista de rutas completas
        self.file_items = {}       # filepath -> QTreeWidgetItem
        self.folder_items = {}     # subfolder -> QTreeWidgetItem
        self.base_folder = ""
        self.worker = None
        self.setup_theme()
        self.setup_ui()
        self.check_mp3gain()

    def setup_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(230, 230, 230))
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(38, 38, 38))
        palette.setColor(QPalette.Text, QColor(230, 230, 230))
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, QColor(230, 230, 230))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        self.setStyleSheet(STYLE)

    def check_mp3gain(self):
        """Verifica que mp3gain esté instalado"""
        try:
            result = subprocess.run(["mp3gain", "-v"], capture_output=True, text=True)
            version = result.stdout.strip() or result.stderr.strip()
            match = re.search(r'(\d+\.\d+\.\d+)', version)
            ver = match.group(1) if match else "desconocida"
            self.statusBar().showMessage(f"mp3gain v{ver} detectado  |  Listo")
        except FileNotFoundError:
            self.statusBar().showMessage("ERROR: mp3gain no encontrado. Instalar con: sudo apt install mp3gain")
            QMessageBox.critical(self, "Error", "mp3gain no esta instalado.\n\nInstalar con:\nsudo apt install mp3gain")

    def log(self, msg):
        """Agrega mensaje al log con timestamp"""
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_log.append(f"[{ts}] {msg}")

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(12, 8, 12, 8)

        # === Drop zone ===
        self.drop_zone = DropZone()
        self.drop_zone.folder_dropped = self.load_folder
        self.drop_zone.btn_browse.clicked.connect(self.browse_folder)
        main_layout.addWidget(self.drop_zone)

        # === Carpeta + info ===
        info = QHBoxLayout()
        self.lbl_folder = QLabel("Carpeta: (ninguna)")
        self.lbl_folder.setStyleSheet("color: #999;")
        self.lbl_count = QLabel("Archivos MP3: 0")
        self.lbl_count.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        info.addWidget(self.lbl_folder, 1)
        info.addWidget(self.lbl_count)
        main_layout.addLayout(info)

        # === Zona media: opciones izq + archivos der ===
        splitter = QSplitter(Qt.Horizontal)

        # --- Panel izquierdo: opciones con scroll ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        opts_container = QWidget()
        opts_container.setStyleSheet("QWidget { background-color: #1e1e1e; }")
        opts_layout = QVBoxLayout(opts_container)
        opts_layout.setSpacing(4)
        opts_layout.setContentsMargins(0, 0, 8, 0)

        # Modo de ganancia
        grp_mode = QGroupBox("Modo de ganancia")
        grp_mode.setToolTip("Elige como quieres que suenen tus canciones:\ntodas igual de fuerte, o respetando como\nsonaban en su album original.")
        grp_mode.setMinimumWidth(340)
        mode_layout = QVBoxLayout(grp_mode)
        mode_layout.setSpacing(6)
        self.rb_track = QRadioButton("Por pista (-r) - Igualar volumen individual")
        self.rb_track.setToolTip("Hace que TODAS las canciones suenen igual de fuerte.\nYa no tendras que subir o bajar el volumen\ncuando cambia la cancion.")
        self.rb_album = QRadioButton("Por album (-a) - Mantener proporcion relativa")
        self.rb_album.setToolTip("Si una cancion del album era mas bajita que otra,\nse queda asi. Solo sube o baja el volumen de\ntodo el album parejo. Ideal para discos completos.")
        self.rb_track.setChecked(True)
        mode_layout.addWidget(self.rb_track)
        mode_layout.addWidget(self.rb_album)
        opts_layout.addWidget(grp_mode)

        # Ajuste de ganancia
        grp_gain = QGroupBox("Ajuste de ganancia")
        grp_gain.setToolTip("Aqui decides que tan fuerte quieres\nque suenen tus canciones.")
        gain_layout = QVBoxLayout(grp_gain)
        gain_layout.setSpacing(10)

        row1 = QHBoxLayout()
        lbl_vol = QLabel("Volumen objetivo:")
        lbl_vol.setToolTip("Que tan fuerte quieres que suenen las canciones.\n89 dB es lo normal. Si lo subes, suenan mas fuerte.\nSi lo bajas, suenan mas bajito.")
        row1.addWidget(lbl_vol)
        self.spin_db = QDoubleSpinBox()
        self.spin_db.setRange(65.0, 105.0)
        self.spin_db.setValue(89.0)
        self.spin_db.setSingleStep(0.5)
        self.spin_db.setSuffix(" dB")
        self.spin_db.setFixedWidth(110)
        self.spin_db.setToolTip("Que tan fuerte quieres que suenen las canciones.\n89 dB es lo normal. Si lo subes, suenan mas fuerte.\nSi lo bajas, suenan mas bajito.")
        row1.addWidget(self.spin_db)
        row1.addStretch()
        gain_layout.addLayout(row1)

        row2 = QHBoxLayout()
        lbl_mod = QLabel("Modificar ganancia:")
        lbl_mod.setToolTip("Un empujoncito extra al volumen.\nNumeros positivos (+) = mas fuerte.\nNumeros negativos (-) = mas bajito.")
        row2.addWidget(lbl_mod)
        self.spin_mod = QSpinBox()
        self.spin_mod.setRange(-20, 20)
        self.spin_mod.setValue(0)
        self.spin_mod.setFixedWidth(110)
        self.spin_mod.setToolTip("Un empujoncito extra al volumen.\nNumeros positivos (+) = mas fuerte.\nNumeros negativos (-) = mas bajito.")
        row2.addWidget(self.spin_mod)
        row2.addStretch()
        gain_layout.addLayout(row2)

        row3 = QHBoxLayout()
        lbl_tag = QLabel("Almacenar tags en:")
        lbl_tag.setToolTip("Donde se guarda la nota de cuanto se cambio el volumen.\nAPE: el que usa mp3gain normalmente.\nID3v2: funciona con mas reproductores de musica.")
        row3.addWidget(lbl_tag)
        self.combo_tag = QComboBox()
        self.combo_tag.addItems(["APE (default)", "ID3v2"])
        self.combo_tag.setFixedWidth(140)
        self.combo_tag.setToolTip("Donde se guarda la nota de cuanto se cambio el volumen.\nAPE: el que usa mp3gain normalmente.\nID3v2: funciona con mas reproductores de musica.")
        row3.addWidget(self.combo_tag)
        row3.addStretch()
        gain_layout.addLayout(row3)

        opts_layout.addWidget(grp_gain)

        # Opciones adicionales
        grp_extra = QGroupBox("Opciones adicionales")
        grp_extra.setToolTip("Opciones extra para que todo salga bien\ny tus canciones no se danen.")
        extra_layout = QVBoxLayout(grp_extra)
        extra_layout.setSpacing(4)

        chks_data = [
            ("Evitar clipping (-k)", True, "k",
             "Si el volumen queda MUY fuerte y la cancion se\nescucharia fea o distorsionada, lo baja tantito\npara que suene bien. Dejalo activado."),
            ("Ignorar clipping (-c)", False, "c",
             "Sube el volumen aunque la cancion se escuche\nfea o tronada. No recomendado, pero util si\nquieres que todo suene parejo a toda costa."),
            ("Preservar fecha original (-p)", True, "p",
             "La fecha del archivo se queda como estaba.\nSin esto, la fecha cambia a la de hoy\ny parece que el archivo es nuevo."),
            ("Usar archivo temporal (-t)", True, "t",
             "Primero guarda los cambios en una copia temporal\ny luego reemplaza el original. Es mas seguro:\nsi algo falla, tu cancion original no se dana."),
            ("Omitir analisis de album (-e)", False, "e",
             "No agrupa las canciones como album.\nActivalo si las canciones son de diferentes\nartistas o albumes mezclados."),
            ("Forzar recalculo (-s r)", False, "sr",
             "Vuelve a analizar todo desde cero, aunque ya\nse haya hecho antes. Util si algo salio mal\nla vez anterior."),
        ]
        self.chk_options = {}
        for text, checked, flag, tooltip in chks_data:
            cb = QCheckBox(text)
            cb.setChecked(checked)
            cb.setToolTip(tooltip)
            self.chk_options[flag] = cb
            extra_layout.addWidget(cb)

        opts_layout.addWidget(grp_extra)

        # Herramientas de tags
        grp_tags = QGroupBox("Herramientas de tags")
        grp_tags.setToolTip("Herramientas para revisar que se hizo,\nborrar las notas guardadas o regresar\nlas canciones a como estaban antes.")
        tags_layout = QVBoxLayout(grp_tags)
        tags_layout.setSpacing(6)

        self.btn_check_tags = QPushButton("Verificar tags (-s c)")
        self.btn_check_tags.setToolTip("Solo mira que cambios se hicieron antes.\nNo toca nada, solo te muestra la informacion.")
        self.btn_check_tags.setEnabled(False)
        self.btn_check_tags.clicked.connect(lambda: self.run_tag_tool(["-s", "c"]))

        self.btn_delete_tags = QPushButton("Eliminar tags (-s d)")
        self.btn_delete_tags.setToolTip("Borra las notas que se guardaron sobre\nlos cambios de volumen. Las canciones\nsiguen sonando igual, solo borra la nota.")
        self.btn_delete_tags.setEnabled(False)
        self.btn_delete_tags.clicked.connect(lambda: self.run_tag_tool(["-s", "d"]))

        self.btn_undo = QPushButton("Deshacer cambios (-u)")
        self.btn_undo.setToolTip("Regresa las canciones a como sonaban antes.\nEs como un CTRL+Z para el volumen.\nSolo funciona si no borraste las notas.")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(lambda: self.run_tag_tool(["-u"]))

        tags_layout.addWidget(self.btn_check_tags)
        tags_layout.addWidget(self.btn_delete_tags)
        tags_layout.addWidget(self.btn_undo)
        opts_layout.addWidget(grp_tags)

        opts_layout.addStretch()
        scroll.setWidget(opts_container)

        # --- Panel derecho ---
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(8, 0, 0, 0)

        lbl_files = QLabel("Archivos MP3 encontrados:")
        lbl_files.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 14px;")
        files_layout.addWidget(lbl_files)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Archivo", "Tamano", "Ganancia", "Estado"])
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        files_layout.addWidget(self.tree, 1)

        # Botones
        btns = QHBoxLayout()
        btns.setSpacing(10)

        self.btn_analyze = QPushButton("Analizar")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setStyleSheet("""
            QPushButton {
                background-color: #1565c0; color: white;
                font-size: 14px; padding: 10px 28px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #1976d2; }
            QPushButton:disabled { background-color: #0d3b6e; color: #666; }
        """)
        self.btn_analyze.clicked.connect(self.analyze)

        self.btn_apply = QPushButton("Aplicar ganancia")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32; color: white;
                font-size: 14px; padding: 10px 28px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:disabled { background-color: #1b4d1e; color: #666; }
        """)
        self.btn_apply.clicked.connect(self.apply_gain)

        self.btn_stop = QPushButton("Detener")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #c62828; color: white;
                font-size: 14px; padding: 10px 28px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #d32f2f; }
            QPushButton:disabled { background-color: #4a1a1a; color: #666; }
        """)
        self.btn_stop.clicked.connect(self.stop_process)

        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #555; color: white;
                font-size: 14px; padding: 10px 28px;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #666; }
        """)
        self.btn_clear.clicked.connect(self.clear_all)

        btns.addWidget(self.btn_analyze)
        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_stop)
        btns.addStretch()
        btns.addWidget(self.btn_clear)
        files_layout.addLayout(btns)

        # Progreso
        grp_progress = QGroupBox("Progreso")
        prog_layout = QVBoxLayout(grp_progress)

        curr = QHBoxLayout()
        lbl_ca = QLabel("Archivo actual:")
        lbl_ca.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        curr.addWidget(lbl_ca)
        self.lbl_current_file = QLabel("-")
        self.lbl_current_file.setStyleSheet("color: #fff; font-weight: bold;")
        curr.addWidget(self.lbl_current_file, 1)
        self.lbl_current_num = QLabel("0 / 0")
        self.lbl_current_num.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 14px;")
        curr.addWidget(self.lbl_current_num)
        prog_layout.addLayout(curr)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Progreso total: %p%")
        prog_layout.addWidget(self.progress_bar)

        files_layout.addWidget(grp_progress)

        # Log
        grp_log = QGroupBox("Registro de actividad")
        log_layout = QVBoxLayout(grp_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(100)
        log_layout.addWidget(self.txt_log)
        files_layout.addWidget(grp_log)

        splitter.addWidget(scroll)
        splitter.addWidget(files_widget)
        splitter.setSizes([380, 650])
        main_layout.addWidget(splitter, 1)

        # === Footer ===
        footer = QHBoxLayout()
        lbl_author = QLabel("Creado por: tuxor.max@gmail.com")
        lbl_author.setStyleSheet("color: #666; font-size: 11px;")
        lbl_version = QLabel(f"{VERSION} {REVISION} | {FECHA_REV}")
        lbl_version.setStyleSheet("color: #666; font-size: 11px;")
        footer.addWidget(lbl_author)
        footer.addStretch()
        footer.addWidget(lbl_version)
        main_layout.addLayout(footer)

        self.statusBar().showMessage("Listo")

    # ==================== FUNCIONALIDAD ====================

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con archivos MP3")
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder):
        """Carga una carpeta y busca MP3 recursivamente"""
        self.base_folder = folder
        self.lbl_folder.setText(f"Carpeta: {folder}")
        self.lbl_folder.setStyleSheet("color: #ccc;")
        self.log(f"Carpeta seleccionada: {folder}")
        self.log("Buscando archivos MP3 recursivamente...")

        self.mp3_files = find_mp3_files(folder)
        total = len(self.mp3_files)

        self.lbl_count.setText(f"Archivos MP3: {total}")
        self.log(f"Se encontraron {total} archivos MP3")

        # Poblar tree
        self.tree.clear()
        self.file_items = {}
        self.folder_items = {}

        for filepath in self.mp3_files:
            rel_path = os.path.relpath(filepath, folder)
            rel_dir = os.path.dirname(rel_path)
            filename = os.path.basename(filepath)

            if not rel_dir or rel_dir == '.':
                rel_dir = "./"

            # Crear nodo de carpeta si no existe
            if rel_dir not in self.folder_items:
                folder_item = QTreeWidgetItem(self.tree, [rel_dir + "/", "", "", ""])
                folder_item.setForeground(0, QColor("#ffb74d"))
                folder_item.setFont(0, QFont("", -1, QFont.Bold))
                folder_item.setExpanded(True)
                self.folder_items[rel_dir] = folder_item

            # Crear nodo de archivo
            size = format_size(os.path.getsize(filepath))
            item = QTreeWidgetItem(self.folder_items[rel_dir], [filename, size, "-", "Pendiente"])
            item.setForeground(3, QColor("#ffa726"))
            self.file_items[filepath] = item

        # Habilitar botones
        has_files = total > 0
        self.btn_analyze.setEnabled(has_files)
        self.btn_apply.setEnabled(has_files)
        self.btn_check_tags.setEnabled(has_files)
        self.btn_delete_tags.setEnabled(has_files)
        self.btn_undo.setEnabled(has_files)

        # Contar carpetas
        n_folders = len(self.folder_items)
        self.log(f"Organizados en {n_folders} carpeta(s)")

    def build_args(self, mode="analyze"):
        """Construye la lista de argumentos para mp3gain"""
        args = []

        # Modo
        if mode == "analyze":
            # Solo analizar, no aplicar
            pass
        elif mode == "apply":
            if self.rb_track.isChecked():
                args.append("-r")
            else:
                args.append("-a")

        # Volumen objetivo (diferencia con 89 dB default)
        target_db = self.spin_db.value()
        if target_db != 89.0:
            diff = target_db - 89.0
            args.extend(["-d", str(diff)])

        # Modificar ganancia
        mod = self.spin_mod.value()
        if mod != 0:
            args.extend(["-m", str(mod)])

        # Opciones adicionales
        if self.chk_options["k"].isChecked():
            args.append("-k")
        if self.chk_options["c"].isChecked():
            args.append("-c")
        if self.chk_options["p"].isChecked():
            args.append("-p")
        if self.chk_options["t"].isChecked():
            args.append("-t")
        else:
            args.append("-T")
        if self.chk_options["e"].isChecked():
            args.append("-e")
        if self.chk_options["sr"].isChecked():
            args.extend(["-s", "r"])

        # Tags
        if self.combo_tag.currentIndex() == 1:
            args.extend(["-s", "i"])

        # Salida tabulada para parseo
        args.append("-o")

        return args

    def set_ui_processing(self, processing):
        """Habilita/deshabilita controles durante el procesamiento"""
        self.btn_analyze.setEnabled(not processing and len(self.mp3_files) > 0)
        self.btn_apply.setEnabled(not processing and len(self.mp3_files) > 0)
        self.btn_stop.setEnabled(processing)
        self.btn_check_tags.setEnabled(not processing and len(self.mp3_files) > 0)
        self.btn_delete_tags.setEnabled(not processing and len(self.mp3_files) > 0)
        self.btn_undo.setEnabled(not processing and len(self.mp3_files) > 0)
        self.drop_zone.setEnabled(not processing)

    def analyze(self):
        """Analiza los archivos sin aplicar cambios"""
        if not self.mp3_files:
            return

        self.log("Iniciando analisis...")
        self.reset_file_states()
        args = self.build_args("analyze")

        self.set_ui_processing(True)
        self.worker = Mp3GainWorker(self.mp3_files, args, "per_file")
        self.connect_worker()
        self.worker.start()

    def apply_gain(self):
        """Aplica la ganancia a los archivos"""
        if not self.mp3_files:
            return

        mode_text = "por pista" if self.rb_track.isChecked() else "por album"
        self.log(f"Aplicando ganancia ({mode_text})...")
        self.reset_file_states()
        args = self.build_args("apply")

        worker_mode = "album" if self.rb_album.isChecked() else "per_file"
        self.set_ui_processing(True)
        self.worker = Mp3GainWorker(self.mp3_files, args, worker_mode)
        self.connect_worker()
        self.worker.start()

    def connect_worker(self):
        """Conecta las señales del worker"""
        self.worker.progress.connect(self.on_progress)
        self.worker.file_result.connect(self.on_file_result)
        self.worker.log_message.connect(self.log)
        self.worker.finished_work.connect(self.on_finished)

    def stop_process(self):
        """Detiene el proceso actual"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("Deteniendo proceso...")

    def on_progress(self, current, total, filename):
        """Actualiza la barra de progreso"""
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"Progreso total: {pct}%  ({current}/{total} archivos)")
        self.lbl_current_file.setText(filename)
        self.lbl_current_num.setText(f"{current} / {total}")

    def on_file_result(self, filepath, gain_info):
        """Actualiza el resultado de un archivo en el tree"""
        if filepath in self.file_items:
            item = self.file_items[filepath]
            item.setText(2, gain_info)
            if "Error" in gain_info:
                item.setText(3, "Error")
                item.setForeground(3, QColor("#ef5350"))
            else:
                item.setText(3, "Procesado")
                item.setForeground(3, QColor("#66bb6a"))

    def on_finished(self, success, message):
        """Cuando el proceso termina"""
        self.set_ui_processing(False)
        self.log(message)
        if success:
            self.statusBar().showMessage("Proceso completado")
        else:
            self.statusBar().showMessage("Proceso detenido o con errores")

    def run_tag_tool(self, extra_args):
        """Ejecuta herramientas de tags"""
        if not self.mp3_files:
            return

        action_names = {
            "c": "Verificando tags",
            "d": "Eliminando tags",
        }
        if "-u" in extra_args:
            action = "Deshaciendo cambios"
        else:
            action = action_names.get(extra_args[-1], "Procesando")

        self.log(f"{action}...")
        self.reset_file_states()
        args = extra_args + ["-o"]

        self.set_ui_processing(True)
        self.worker = Mp3GainWorker(self.mp3_files, args, "per_file")
        self.connect_worker()
        self.worker.start()

    def reset_file_states(self):
        """Resetea el estado de todos los archivos a Pendiente"""
        for filepath, item in self.file_items.items():
            item.setText(2, "-")
            item.setText(3, "Pendiente")
            item.setForeground(3, QColor("#ffa726"))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Progreso total: 0%")
        self.lbl_current_file.setText("-")
        self.lbl_current_num.setText("0 / 0")

    def clear_all(self):
        """Limpia todo"""
        self.tree.clear()
        self.mp3_files = []
        self.file_items = {}
        self.folder_items = {}
        self.base_folder = ""
        self.lbl_folder.setText("Carpeta: (ninguna)")
        self.lbl_folder.setStyleSheet("color: #999;")
        self.lbl_count.setText("Archivos MP3: 0")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Progreso total: 0%")
        self.lbl_current_file.setText("-")
        self.lbl_current_num.setText("0 / 0")
        self.txt_log.clear()
        self.btn_analyze.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.btn_check_tags.setEnabled(False)
        self.btn_delete_tags.setEnabled(False)
        self.btn_undo.setEnabled(False)
        self.log("Limpiado")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = NiveladorGUI()
    w.show()
    sys.exit(app.exec_())
