from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QTextEdit, QSplitter, QGroupBox,
    QMessageBox, QComboBox,
)

from src.mediahub.docs.help_loader import HelpLoader
from src.mediahub.docs.manual_loader import load_extra_manual_entries
from src.mediahub.docs.plugin_help import load_plugin_help


class HelpCenter(QWidget):
    """Interaktives Hilfe-Center für MediaHub."""

    def __init__(self, base_dir=None, parent=None):
        super().__init__(parent)

        self.base_dir = Path(base_dir or Path.cwd())
        self.callbacks = {}
        self.loader = HelpLoader(self.base_dir)

        self.entries = self._load_entries()
        self.visible_entries = []

        self._build_ui()
        self.filter_entries("")
        self.topic_list.setCurrentRow(0)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("❓ Hilfe-Center")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        search_row = QHBoxLayout()

        self.book_filter = QComboBox()
        self.book_filter.addItem("Alle Bereiche", "all")
        self.book_filter.addItem("Schnellstart", "quick")
        self.book_filter.addItem("Handbuch", "user")
        self.book_filter.addItem("Entwickler", "developer")
        self.book_filter.addItem("Plugins", "plugin")
        self.book_filter.currentIndexChanged.connect(
            lambda: self.filter_entries(self.search_input.text())
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suche in der Hilfe ...")
        self.search_input.textChanged.connect(self.filter_entries)

        search_row.addWidget(self.book_filter)
        search_row.addWidget(self.search_input, 1)
        layout.addLayout(search_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.topic_list = QListWidget()
        self.topic_list.currentRowChanged.connect(self.show_entry)
        splitter.addWidget(self.topic_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.entry_title = QLabel("Hilfe")
        self.entry_title.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.entry_text = QTextEdit()
        self.entry_text.setReadOnly(True)

        button_row = QHBoxLayout()

        self.btn_open_area = QPushButton("Bereich öffnen")
        self.btn_open_area.clicked.connect(self.open_current_area)

        self.btn_pdf = QPushButton("PDF öffnen")
        self.btn_pdf.clicked.connect(lambda: self.open_current_document("pdf"))

        self.btn_html = QPushButton("HTML öffnen")
        self.btn_html.clicked.connect(lambda: self.open_current_document("html"))

        self.btn_docs_folder = QPushButton("Dokumente öffnen")
        self.btn_docs_folder.clicked.connect(self.open_docs_folder)

        button_row.addWidget(self.btn_open_area)
        button_row.addWidget(self.btn_pdf)
        button_row.addWidget(self.btn_html)
        button_row.addWidget(self.btn_docs_folder)
        button_row.addStretch(1)

        self.assistant_box = QGroupBox("Interaktive Hilfe")
        assistant_layout = QVBoxLayout(self.assistant_box)

        self.assistant_text = QLabel(
            "Tipp: Wähle links ein Thema aus oder suche nach einem Begriff."
        )
        self.assistant_text.setWordWrap(True)

        assistant_buttons = QHBoxLayout()

        self.btn_health = QPushButton("🩺 Health Check")
        self.btn_health.clicked.connect(lambda: self._run_callback("health"))

        self.btn_recovery = QPushButton("🛟 Recovery Center")
        self.btn_recovery.clicked.connect(lambda: self._run_callback("recovery"))

        self.btn_settings = QPushButton("⚙ Einstellungen")
        self.btn_settings.clicked.connect(lambda: self._run_callback("settings"))

        assistant_buttons.addWidget(self.btn_health)
        assistant_buttons.addWidget(self.btn_recovery)
        assistant_buttons.addWidget(self.btn_settings)
        assistant_buttons.addStretch(1)

        assistant_layout.addWidget(self.assistant_text)
        assistant_layout.addLayout(assistant_buttons)

        right_layout.addWidget(self.entry_title)
        right_layout.addWidget(self.entry_text, 1)
        right_layout.addLayout(button_row)
        right_layout.addWidget(self.assistant_box)

        splitter.addWidget(right)
        splitter.setSizes([300, 760])

        layout.addWidget(splitter, 1)

    def set_callbacks(self, callbacks: dict):
        self.callbacks = callbacks or {}

    def _load_entries(self):
        entries = []

        for item in self.loader.load():
            book = item.get("book", "user")
            entries.append(self._normalize_entry(item, book))

        for item in load_extra_manual_entries(self.loader):
            book = item.get("book", "user")
            entries.append(self._normalize_entry(item, book))

        for item in load_plugin_help(self.base_dir):
            entries.append(self._normalize_entry(item, "plugin"))

        if entries:
            return entries

        return self._fallback_entries()

    def _normalize_entry(self, item: dict, book: str) -> dict:
        raw_title = item.get("raw_title") or item.get("title", "Hilfe")

        return {
            "title": self._display_title(book, raw_title),
            "raw_title": raw_title,
            "key": item.get("key", ""),
            "book": book,
            "keywords": item.get("keywords", ""),
            "text": item.get("text", ""),
            "source": item.get("source", ""),
        }

    def _display_title(self, book: str, title: str) -> str:
        if book == "quick":
            return f"🚀 {title}"
        if book == "developer":
            return f"📙 {title}"
        if book == "plugin":
            return f"🔌 {title}"
        return f"📘 {title}"

    def _fallback_entries(self):
        return [
            {
                "title": "🚀 Erste Schritte",
                "raw_title": "Erste Schritte",
                "key": "setup",
                "book": "quick",
                "keywords": "start einrichtung erster start",
                "text": (
                    "Erste Schritte\n\n"
                    "MediaHub wurde gestartet, aber die aktuelle Hilfe-Datenbank "
                    "wurde nicht gefunden.\n\n"
                    "Führe im Projektordner aus:\n\n"
                    "python build_docs.py\n\n"
                    "Danach wird die Hilfe automatisch aus docs_source erzeugt."
                ),
                "source": "",
            }
        ]

    def filter_entries(self, text):
        query = (text or "").strip().lower()
        book_filter = self.book_filter.currentData()

        self.topic_list.clear()
        self.visible_entries = []

        for entry in self.entries:
            book = entry.get("book", "user")

            if book_filter != "all" and book_filter != book:
                continue

            haystack = (
                f"{entry.get('title', '')} "
                f"{entry.get('raw_title', '')} "
                f"{entry.get('keywords', '')} "
                f"{entry.get('text', '')}"
            ).lower()

            if not query or query in haystack:
                self.visible_entries.append(entry)
                self.topic_list.addItem(entry["title"])

        if self.topic_list.count() > 0 and self.topic_list.currentRow() < 0:
            self.topic_list.setCurrentRow(0)

        if self.topic_list.count() == 0:
            self.entry_title.setText("Keine Treffer")
            self.entry_text.setPlainText(
                "Für diese Suche wurde kein Hilfethema gefunden."
            )
            self.btn_open_area.setEnabled(False)

    def show_entry(self, row):
        if row < 0 or row >= len(self.visible_entries):
            return

        entry = self.visible_entries[row]

        self.entry_title.setText(entry["title"])
        self.entry_text.setPlainText(entry["text"])

        key = entry.get("key")
        self.btn_open_area.setEnabled(key in self.callbacks)

        book = entry.get("book", "user")

        if key in self.callbacks:
            self.assistant_text.setText(
                "Tipp: Mit 'Bereich öffnen' springst du direkt dorthin."
            )
        elif book == "quick":
            self.assistant_text.setText("Schnellstart: die wichtigsten Schritte.")
        elif book == "developer":
            self.assistant_text.setText("Entwicklerhilfe: Technik, Build und Plugins.")
        elif book == "plugin":
            self.assistant_text.setText("Dieses Hilfethema kommt von einem Plugin.")
        else:
            self.assistant_text.setText("Benutzerhandbuch zur Bedienung von MediaHub.")

    def open_current_area(self):
        row = self.topic_list.currentRow()

        if row < 0 or row >= len(self.visible_entries):
            return

        self._run_callback(self.visible_entries[row].get("key"))

    def _run_callback(self, key):
        callback = self.callbacks.get(key)

        if callback is not None:
            callback()

    def open_current_document(self, file_type: str):
        row = self.topic_list.currentRow()

        if row < 0 or row >= len(self.visible_entries):
            return

        self.open_document(self.visible_entries[row].get("book", "user"), file_type)

    def open_document(self, book: str, file_type: str):
        docs = {
            "quick": {
                "pdf": "quick/MediaHub_Kurzanleitung.pdf",
                "html": "quick/MediaHub_Kurzanleitung.html",
            },
            "user": {
                "pdf": "MediaHub_Handbuch.pdf",
                "html": "MediaHub_Handbuch.html",
            },
            "developer": {
                "pdf": "developer/MediaHub_Entwicklerhandbuch.pdf",
                "html": "developer/MediaHub_Entwicklerhandbuch.html",
            },
        }

        if book == "plugin":
            self.open_docs_folder()
            return

        relative = docs.get(book, docs["user"]).get(file_type)
        path = self.loader.first_existing_doc(relative)

        if path is None:
            QMessageBox.warning(
                self,
                "Dokument nicht gefunden",
                f"Die Datei wurde nicht gefunden:\n\n{relative}\n\n"
                "Bitte zuerst build_docs.py ausführen.",
            )
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_manual(self):
        self.open_document("user", "pdf")

    def open_html_manual(self):
        self.open_document("user", "html")

    def open_docs_folder(self):
        for folder in self.loader.candidate_dirs():
            if folder.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
                return

        QMessageBox.warning(
            self,
            "Dokumente",
            "Der Dokumentationsordner wurde nicht gefunden.",
        )