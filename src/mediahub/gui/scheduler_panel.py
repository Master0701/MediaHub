from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt


class SchedulerPanel(QWidget):
    """Einfache Scheduler-Ansicht.

    v0.9.4 zeigt Aufgaben und die Scheduler-Automatik. Fällige Aufgaben
    erzeugen weiterhin Jobs über die Job-Queue.
    """

    def __init__(self, repository=None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.add_current_channel_callback = None
        self.add_current_channel_sync_download_callback = None
        self.add_current_channel_sync_auto_download_callback = None
        self.create_due_jobs_callback = None
        self.run_selected_now_callback = None
        self.delete_selected_callback = None
        self.set_enabled_callback = None
        self.toggle_automatic_callback = None
        self.check_now_callback = None
        self.status_provider = None
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Scheduler")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.info_label = QLabel("Bereit")

        self.interval_combo = QComboBox()
        self.interval_combo.addItem("1 Stunde", 1)
        self.interval_combo.addItem("3 Stunden", 3)
        self.interval_combo.addItem("6 Stunden", 6)
        self.interval_combo.addItem("12 Stunden", 12)
        self.interval_combo.addItem("24 Stunden", 24)
        self.interval_combo.addItem("7 Tage", 24 * 7)
        self.interval_combo.setCurrentIndex(4)

        self.btn_add_current = QPushButton("Sync-Aufgabe")
        self.btn_add_sync_download = QPushButton("Sync+Auswahl")
        self.btn_add_sync_auto_download = QPushButton("Auto-Download")
        self.btn_auto = QPushButton("Automatik")
        self.btn_check_now = QPushButton("Jetzt prüfen")
        self.btn_due = QPushButton("Fällige Jobs")
        self.btn_run_now = QPushButton("Jetzt Job")
        self.btn_delete = QPushButton("Löschen")
        self.btn_refresh = QPushButton("Aktualisieren")

        self.btn_add_current.setToolTip("Für den aktuellen Kanal eine reine Sync-Aufgabe anlegen")
        self.btn_add_sync_download.setToolTip("Für den aktuellen Kanal eine Aufgabe anlegen: Sync und danach neue Videos zur Download-Auswahl öffnen")
        self.btn_add_sync_auto_download.setToolTip("Für den aktuellen Kanal eine Aufgabe anlegen: Sync und neue Videos automatisch herunterladen")
        self.btn_auto.setToolTip("Automatische Scheduler-Prüfung ein- oder ausschalten")
        self.btn_check_now.setToolTip("Sofort prüfen, ob Aufgaben fällig sind")
        self.btn_due.setToolTip("Aus allen fälligen Aufgaben Jobs erzeugen")
        self.btn_run_now.setToolTip("Für die ausgewählte Aufgabe sofort einen Job erzeugen")

        self.btn_add_current.clicked.connect(self.add_current_channel)
        self.btn_add_sync_download.clicked.connect(self.add_current_channel_sync_download)
        self.btn_add_sync_auto_download.clicked.connect(self.add_current_channel_sync_auto_download)
        self.btn_auto.clicked.connect(self.toggle_automatic)
        self.btn_check_now.clicked.connect(self.check_now)
        self.btn_due.clicked.connect(self.create_due_jobs)
        self.btn_run_now.clicked.connect(self.run_selected_now)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_refresh.clicked.connect(self.refresh)

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QLabel("Intervall:"))
        header.addWidget(self.interval_combo)
        header.addWidget(self.info_label)
        header.addWidget(self.btn_auto)
        header.addWidget(self.btn_check_now)
        header.addWidget(self.btn_add_current)
        header.addWidget(self.btn_add_sync_download)
        header.addWidget(self.btn_add_sync_auto_download)
        header.addWidget(self.btn_due)
        header.addWidget(self.btn_run_now)
        header.addWidget(self.btn_delete)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Aktiv", "Typ", "Name", "Kanal", "Intervall", "Nächster Lauf", "Letzter Lauf"
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
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.refresh()

    def set_callbacks(
        self,
        add_current_channel_callback=None,
        add_current_channel_sync_download_callback=None,
        add_current_channel_sync_auto_download_callback=None,
        create_due_jobs_callback=None,
        run_selected_now_callback=None,
        delete_selected_callback=None,
        toggle_automatic_callback=None,
        check_now_callback=None,
        status_provider=None,
    ):
        self.add_current_channel_callback = add_current_channel_callback
        self.add_current_channel_sync_download_callback = add_current_channel_sync_download_callback
        self.add_current_channel_sync_auto_download_callback = add_current_channel_sync_auto_download_callback
        self.create_due_jobs_callback = create_due_jobs_callback
        self.run_selected_now_callback = run_selected_now_callback
        self.delete_selected_callback = delete_selected_callback
        self.toggle_automatic_callback = toggle_automatic_callback
        self.check_now_callback = check_now_callback
        self.status_provider = status_provider

    def selected_interval_hours(self) -> int:
        return int(self.interval_combo.currentData() or 24)

    def selected_task_id(self):
        row = self.table.currentRow()
        if row < 0:
            self.info_label.setText("Keine Aufgabe ausgewählt")
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        task_id = item.data(Qt.ItemDataRole.UserRole)
        return int(task_id) if task_id else None

    def add_current_channel(self):
        if self.add_current_channel_callback is not None:
            self.add_current_channel_callback(self.selected_interval_hours())

    def add_current_channel_sync_download(self):
        if self.add_current_channel_sync_download_callback is not None:
            self.add_current_channel_sync_download_callback(self.selected_interval_hours())

    def add_current_channel_sync_auto_download(self):
        if self.add_current_channel_sync_auto_download_callback is not None:
            self.add_current_channel_sync_auto_download_callback(self.selected_interval_hours())

    def toggle_automatic(self):
        if self.toggle_automatic_callback is not None:
            self.toggle_automatic_callback()
        self.refresh()

    def check_now(self):
        if self.check_now_callback is not None:
            self.check_now_callback()
        self.refresh()

    def create_due_jobs(self):
        if self.create_due_jobs_callback is not None:
            self.create_due_jobs_callback()

    def run_selected_now(self):
        task_id = self.selected_task_id()
        if task_id and self.run_selected_now_callback is not None:
            self.run_selected_now_callback(task_id)

    def delete_selected(self):
        task_id = self.selected_task_id()
        if task_id and self.delete_selected_callback is not None:
            self.delete_selected_callback(task_id)

    def refresh(self):
        if self.repository is None:
            self.info_label.setText("Keine Datenbank")
            self.table.setRowCount(0)
            return

        tasks = self.repository.get_scheduled_tasks(limit=200)
        self.table.setRowCount(0)
        for task in tasks:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                task.get("id", ""),
                "✓" if task.get("enabled") else "-",
                self._type_text(task.get("task_type", "")),
                task.get("name", ""),
                task.get("channel_name", ""),
                self._interval_text(task.get("interval_hours", 0)),
                task.get("next_run_at", "") or "fällig",
                task.get("last_run_at", "") or "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, int(task.get("id", 0) or 0))
                self.table.setItem(row, col, item)

        due = sum(1 for task in tasks if task.get("is_due"))
        enabled = sum(1 for task in tasks if task.get("enabled"))
        auto_text = self.status_provider() if self.status_provider is not None else "Automatik: ?"
        self.info_label.setText(f"{len(tasks)} Aufgaben | {enabled} aktiv | {due} fällig | {auto_text}")

    def _type_text(self, task_type: str) -> str:
        mapping = {
            "sync_channel": "🔄 Sync",
            "sync_download_channel": "🔄⬇ Sync+Auswahl",
            "sync_auto_download_channel": "🔄⬇ Auto-Download",
            "backup": "💾 Backup",
            "download_new": "⬇ Neue laden",
        }
        return mapping.get(task_type or "", task_type or "")

    def _interval_text(self, hours) -> str:
        try:
            hours = int(hours or 0)
        except (TypeError, ValueError):
            hours = 0
        if hours >= 24 and hours % 24 == 0:
            days = hours // 24
            return f"{days} Tag" if days == 1 else f"{days} Tage"
        return f"{hours} Std."
