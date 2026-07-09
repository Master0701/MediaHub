from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QListWidget, QProgressBar, QTextEdit
)


class AssistantPanel(QWidget):
    """MediaHub Assistent fuer RC9.2."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("🤖 MediaHub Assistent")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.updated_label = QLabel("Noch nicht geprüft")
        self.updated_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.btn_refresh = QPushButton("Prüfen")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.updated_label)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        score_box = QGroupBox("Gesamtzustand")
        score_layout = QVBoxLayout(score_box)
        self.headline = QLabel("Assistent bereit.")
        self.score_label = QLabel("Health Score: - %")
        self.score_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        score_layout.addWidget(self.headline)
        score_layout.addWidget(self.score_label)
        score_layout.addWidget(self.score_bar)
        layout.addWidget(score_box)

        self.check_list = QListWidget()
        layout.addWidget(self.check_list, 1)

        action_box = QGroupBox("Schnellaktionen")
        action_layout = QHBoxLayout(action_box)
        self.btn_backup = QPushButton("Backup erstellen")
        self.btn_optimize = QPushButton("Datenbank optimieren")
        self.btn_backup.clicked.connect(self.create_backup)
        self.btn_optimize.clicked.connect(self.optimize_database)
        action_layout.addWidget(self.btn_backup)
        action_layout.addWidget(self.btn_optimize)
        action_layout.addStretch(1)
        layout.addWidget(action_box)

        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(90)
        info.setPlainText(
            "RC9.2: Der Assistent prüft Tools, Datenbank, Backups, Scheduler, "
            "Downloadordner, Schreibrechte und freien Speicher. Kritische Punkte "
            "stehen immer oben."
        )
        layout.addWidget(info)

    def set_manager(self, manager):
        self.manager = manager

    def refresh(self):
        if self.manager is not None:
            self.manager.refresh()

    def create_backup(self):
        if self.manager is not None:
            self.manager.create_backup()

    def optimize_database(self):
        if self.manager is not None:
            self.manager.optimize_database()

    def load_report(self, report: dict):
        score = int(report.get("score") or 0)
        self.score_bar.setValue(score)
        self.score_label.setText(f"Health Score: {score} %")
        self.headline.setText(report.get("headline") or "Prüfung abgeschlossen.")
        self.updated_label.setText(f"Stand: {report.get('updated_at', '-')}")

        self.check_list.clear()
        for check in report.get("checks", []):
            action = check.get("action") or ""
            suffix = f"  → {action}" if action else ""
            self.check_list.addItem(
                f"{check.get('icon', '⚪')} {check.get('area')} · {check.get('title')}: "
                f"{check.get('message')}{suffix}"
            )
