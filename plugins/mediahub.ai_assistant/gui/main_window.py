from __future__ import annotations

import json

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
        QTabWidget, QVBoxLayout, QWidget
    )
except ImportError:  # Die Plugin-Prüfung soll auch ohne gestartete GUI funktionieren.
    QDialog = object


class AIAssistantWindow(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle(f"MediaHub KI-Assistent {plugin.VERSION}")
        self.resize(900, 620)

        title = QLabel("MediaHub KI-Assistent")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")

        subtitle = QLabel(
            "Grundsystem aktiv – schnelle Wissensdatenbank, schreibgeschützter "
            "MediaHub-Zugriff und Vorbereitung der Medienerkennung."
        )
        subtitle.setWordWrap(True)

        self.tabs = QTabWidget()
        self.status_text = QPlainTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setLineWrapMode(QPlainTextEdit.NoWrap)

        status_page = QWidget()
        status_layout = QVBoxLayout(status_page)
        status_layout.addWidget(self.status_text)

        roadmap_text = QPlainTextEdit()
        roadmap_text.setReadOnly(True)
        roadmap_text.setPlainText(
            "Nächste Schritte:\n\n"
            "• Such- und Beziehungs-Engine\n"
            "• Bestandsvergleich mit MediaHub\n"
            "• gestufte Videodatei-Analyse\n"
            "• Film-/Serien- und Editionserkennung\n"
            "• optionaler austauschbarer KI-Provider\n\n"
            "Die KI wird nicht für einfache Datenbankabfragen benötigt."
        )
        roadmap_page = QWidget()
        roadmap_layout = QVBoxLayout(roadmap_page)
        roadmap_layout.addWidget(roadmap_text)

        self.tabs.addTab(status_page, "Systemstatus")
        self.tabs.addTab(roadmap_page, "Ausbauplan")

        refresh = QPushButton("Status aktualisieren")
        refresh.clicked.connect(self.refresh_status)
        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(refresh)
        buttons.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(buttons)
        self.refresh_status()

    def refresh_status(self):
        self.status_text.setPlainText(
            json.dumps(self.plugin.get_status(), ensure_ascii=False, indent=2)
        )
