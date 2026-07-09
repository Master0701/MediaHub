from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)


class JobQueuePanel(QWidget):
    """Anzeige und manuelle Steuerung der internen Auftragswarteschlange."""

    def __init__(self, repository=None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.execute_next_callback = None
        self.execute_selected_callback = None

        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("🧩 Job-Queue")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.info_label = QLabel("Bereit")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.btn_run_next = QPushButton("Nächsten starten")
        self.btn_run_selected = QPushButton("Auswahl starten")
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_clear_done = QPushButton("Erledigte löschen")

        self.btn_run_next.clicked.connect(self.run_next)
        self.btn_run_selected.clicked.connect(self.run_selected)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_clear_done.clicked.connect(self.clear_finished)

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.info_label)
        header.addWidget(self.btn_run_next)
        header.addWidget(self.btn_run_selected)
        header.addWidget(self.btn_refresh)
        header.addWidget(self.btn_clear_done)
        layout.addLayout(header)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Status", "Typ", "Name", "Kanal", "Geplant", "Erstellt"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.refresh()

    def set_execute_next_callback(self, callback):
        self.execute_next_callback = callback

    def set_execute_selected_callback(self, callback):
        self.execute_selected_callback = callback

    def refresh(self):
        if self.repository is None:
            self.info_label.setText("Keine Datenbank")
            self.table.setRowCount(0)
            return

        jobs = self.repository.get_jobs(limit=200)
        self.table.setRowCount(0)
        for job in jobs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                job.get("id", ""),
                self._status_text(job.get("status", "pending")),
                self._type_text(job.get("job_type", "")),
                job.get("title", ""),
                job.get("channel_name", ""),
                self._planned_text(job.get("scheduled_at", "")),
                job.get("created_at", "") or "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, int(job.get("id", 0) or 0))
                self.table.setItem(row, col, item)

        pending = sum(1 for job in jobs if job.get("status") == "pending")
        running = sum(1 for job in jobs if job.get("status") == "running")
        failed = sum(1 for job in jobs if job.get("status") == "failed")
        self.info_label.setText(f"{len(jobs)} Jobs | {pending} wartend | {running} läuft | {failed} Fehler")

    def run_next(self):
        if self.execute_next_callback is not None:
            self.execute_next_callback()

    def run_selected(self):
        if self.execute_selected_callback is None:
            return
        row = self.table.currentRow()
        if row < 0:
            self.info_label.setText("Kein Job ausgewählt")
            return
        item = self.table.item(row, 0)
        job_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if job_id:
            self.execute_selected_callback(int(job_id))

    def clear_finished(self):
        if self.repository is None:
            return
        removed = self.repository.clear_finished_jobs()
        self.refresh()
        self.info_label.setText(f"{removed} erledigte Jobs gelöscht")


    def _planned_text(self, scheduled_at: str) -> str:
        value = (scheduled_at or "").strip()
        if not value:
            return "Manuell / sofort"
        return value

    def _status_text(self, status: str) -> str:
        mapping = {
            "pending": "⏳ Wartet",
            "running": "▶ Läuft",
            "done": "✅ Fertig",
            "failed": "❌ Fehler",
            "cancelled": "⛔ Abbruch",
        }
        return mapping.get(status or "pending", status or "pending")

    def _type_text(self, job_type: str) -> str:
        mapping = {
            "sync_channel": "🔄 Sync",
            "sync_download_channel": "🔄⬇ Sync+Auswahl",
            "sync_auto_download_channel": "🔄⬇ Auto-Download",
            "download_queue": "⬇ Download",
        }
        return mapping.get(job_type or "", job_type or "")
