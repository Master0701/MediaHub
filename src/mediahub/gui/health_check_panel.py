from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)
from PySide6.QtCore import Qt


class HealthCheckPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.check_callback = None
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("🩺 Health Check")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.btn_refresh = QPushButton("Jetzt prüfen")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.summary = QLabel("Prüft Tools, Datenbank, Ordner und Schreibrechte.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Status", "Bereich", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

        self.hints = QTextEdit()
        self.hints.setReadOnly(True)
        self.hints.setMaximumHeight(120)
        self.hints.setPlainText(
            "Hinweis: Fehlende Tools können im Tool-Center installiert oder geprüft werden. "
            "Fehlende Ordner werden beim Health Check nach Möglichkeit automatisch angelegt."
        )
        layout.addWidget(self.hints)

    def set_check_callback(self, callback):
        self.check_callback = callback

    def refresh(self):
        if self.check_callback is None:
            self.summary.setText("Health Check ist noch nicht verbunden.")
            return

        results = self.check_callback(as_rows=True)
        ok_count = sum(1 for row in results if row.get("ok"))
        warn_count = len(results) - ok_count
        self.summary.setText(f"Ergebnis: {ok_count} OK, {warn_count} Warnung(en).")

        self.table.setRowCount(0)
        for result in results:
            row = self.table.rowCount()
            self.table.insertRow(row)
            status = "✓ OK" if result.get("ok") else "⚠ Prüfen"
            self.table.setItem(row, 0, QTableWidgetItem(status))
            self.table.setItem(row, 1, QTableWidgetItem(str(result.get("name", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(result.get("detail", ""))))
