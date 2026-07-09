from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QGroupBox, QListWidget, QSplitter, QProgressBar,
    QSizePolicy
)


class DashboardPanel(QWidget):
    """Dashboard Pro für MediaHub RC9.3.

    Das Panel bleibt defensiv: Es funktioniert auch ohne Manager-Callbacks,
    zeigt dann aber nur die vorhandenen Datenbankinformationen an.
    """

    def __init__(self, repository=None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.quick_actions = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("📊 Dashboard Pro")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.subtitle = QLabel("Zentrale Übersicht")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.setMinimumHeight(34)
        self.btn_refresh.setToolTip("Dashboard, Assistent und Listen neu laden.")
        self.btn_refresh.clicked.connect(self.refresh)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.subtitle)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setHandleWidth(8)
        top_splitter.addWidget(self._build_stats_box())
        top_splitter.addWidget(self._build_assistant_box())
        top_splitter.addWidget(self._build_quick_actions_box())
        top_splitter.setSizes([520, 390, 300])
        layout.addWidget(top_splitter, 0)

        middle_splitter = QSplitter(Qt.Orientation.Horizontal)
        middle_splitter.setHandleWidth(8)
        self.last_downloads_list = self._make_list_box(middle_splitter, "Letzte Downloads")
        self.last_jobs_list = self._make_list_box(middle_splitter, "Letzte Jobs / Fehler")
        self.notifications_list = self._make_list_box(middle_splitter, "🔔 Benachrichtigungen")
        middle_splitter.setSizes([430, 430, 330])
        layout.addWidget(middle_splitter, 1)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.setHandleWidth(8)
        self.new_list = self._make_list_box(bottom_splitter, "Neue Videos")
        self.recent_list = self._make_list_box(bottom_splitter, "Zuletzt erkannt")
        self.last_syncs_list = self._make_list_box(bottom_splitter, "Letzte Synchronisierungen")
        bottom_splitter.setSizes([400, 400, 400])
        layout.addWidget(bottom_splitter, 1)

        self.refresh()

    def _build_stats_box(self):
        self.stats_box = QGroupBox("Gesamtstatus")
        stats_layout = QGridLayout(self.stats_box)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setHorizontalSpacing(16)
        stats_layout.setVerticalSpacing(8)

        self.stat_labels = {}
        stats = [
            ("channels", "📺 Kanäle"),
            ("playlists", "📂 Playlists"),
            ("videos", "🎬 Videos"),
            ("new_videos", "⭐ Neue"),
            ("downloads_today", "⬇ Heute"),
            ("active_jobs", "📋 Jobs"),
            ("scheduler_status", "⏰ Scheduler"),
            ("health_status", "❤️ Health"),
            ("downloaded_videos", "✅ Geladen"),
            ("members_only_videos", "🔵 Mitglieder"),
            ("last_sync", "🔄 Letzte Sync"),
            ("db_size", "🗄 Datenbank"),
        ]
        for index, (key, label_text) in enumerate(stats):
            row = index // 3
            col = (index % 3) * 2
            label = QLabel(label_text + ":")
            value = QLabel("-")
            value.setStyleSheet("font-size: 14px; font-weight: bold;")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            stats_layout.addWidget(label, row, col)
            stats_layout.addWidget(value, row, col + 1)
            self.stat_labels[key] = value
        return self.stats_box

    def _build_assistant_box(self):
        assistant_box = QGroupBox("🤖 Assistent")
        assistant_layout = QVBoxLayout(assistant_box)
        assistant_layout.setContentsMargins(12, 12, 12, 12)
        assistant_layout.setSpacing(8)

        self.assistant_score = QLabel("Health Score: - %")
        self.assistant_score.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.assistant_progress = QProgressBar()
        self.assistant_progress.setRange(0, 100)
        self.assistant_progress.setValue(0)
        self.assistant_progress.setTextVisible(True)
        self.assistant_headline = QLabel("Noch nicht geprüft")
        self.assistant_headline.setWordWrap(True)
        self.assistant_list = QListWidget()
        self.assistant_list.setMinimumHeight(120)

        action_row = QHBoxLayout()
        self.btn_assistant_open = QPushButton("Assistent öffnen")
        self.btn_assistant_open.setMinimumHeight(32)
        self.btn_assistant_open.clicked.connect(lambda: self._run_action("assistant"))
        self.btn_assistant_backup = QPushButton("Backup")
        self.btn_assistant_backup.setMinimumHeight(32)
        self.btn_assistant_backup.clicked.connect(lambda: self._run_action("backup"))
        action_row.addWidget(self.btn_assistant_open)
        action_row.addWidget(self.btn_assistant_backup)

        assistant_layout.addWidget(self.assistant_score)
        assistant_layout.addWidget(self.assistant_progress)
        assistant_layout.addWidget(self.assistant_headline)
        assistant_layout.addWidget(self.assistant_list, 1)
        assistant_layout.addLayout(action_row)
        return assistant_box

    def _build_quick_actions_box(self):
        box = QGroupBox("⚡ Schnellaktionen")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)

        self.quick_buttons = {}
        actions = [
            ("channel", "➕ Kanal hinzufügen", "Neuen Kanal über die Kanalverwaltung anlegen."),
            ("playlist", "📋 Playlist-Manager", "Playlist-Manager öffnen."),
            ("downloads", "⬇ Downloads", "Download-Warteschlange öffnen."),
            ("backup", "💾 Backup erstellen", "Sofort ein Backup im Recovery Center erstellen."),
            ("health", "❤️ Health Check", "Systemprüfung öffnen."),
            ("settings", "⚙ Einstellungen", "Globale Einstellungen öffnen."),
            ("help", "❓ Hilfe-Center", "Hilfe-Center öffnen."),
        ]
        for key, text, tooltip in actions:
            button = QPushButton(text)
            button.setMinimumHeight(34)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda checked=False, name=key: self._run_action(name))
            layout.addWidget(button)
            self.quick_buttons[key] = button

        layout.addStretch(1)
        return box

    def _make_list_box(self, parent, title):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        list_widget = QListWidget()
        list_widget.setMinimumHeight(130)
        layout.addWidget(list_widget)
        parent.addWidget(box)
        return list_widget

    def set_quick_actions(self, actions: dict):
        """Callbacks aus MainWindow setzen."""
        self.quick_actions = actions or {}

    def _run_action(self, key: str):
        callback = self.quick_actions.get(key)
        if callable(callback):
            callback()

    def refresh(self):
        if self.repository is None:
            self.subtitle.setText("Keine Datenbank verfügbar")
            self._fill_list(self.notifications_list, [], lambda row: str(row), "Keine Datenbank verfügbar.")
            return

        stats = self.repository.get_dashboard_stats()
        for key, label in self.stat_labels.items():
            label.setText(str(stats.get(key, "-") or "-"))

        self._fill_list(
            self.new_list,
            self.repository.get_recent_library_videos(status_filter="new", limit=25),
            lambda video: f"🟡 {video.get('title') or 'Ohne Titel'} — {video.get('channel_name') or 'Unbekannt'} {video.get('upload_date') or ''}",
            "Keine neuen Videos markiert."
        )
        self._fill_list(
            self.recent_list,
            self.repository.get_recent_library_videos(status_filter="all", limit=25),
            lambda video: f"{self._status_icon(video)} {video.get('title') or 'Ohne Titel'} — {video.get('channel_name') or 'Unbekannt'}",
            "Noch keine Videos in der Datenbank."
        )
        summary = self.repository.get_statistics_summary()
        self._fill_list(
            self.last_downloads_list,
            summary.get("recent_downloads", []),
            lambda row: f"⬇ {row.get('title') or row.get('filename') or row.get('video_id') or 'Unbekannt'} — {row.get('channel_name') or 'Unbekannt'}",
            "Noch keine Downloads."
        )
        self._fill_list(
            self.last_jobs_list,
            self._get_recent_jobs(),
            lambda row: f"📋 {row.get('status') or '-'} — {row.get('title') or row.get('job_type') or 'Job'} {row.get('error_message') or ''}",
            "Noch keine Jobs."
        )
        self._fill_list(
            self.last_syncs_list,
            summary.get("top_channels", [])[:10],
            lambda row: f"🔄 {row.get('name') or 'Unbekannt'} — {row.get('video_count', 0)} Videos",
            "Noch keine Sync-Daten."
        )

    def _fill_list(self, list_widget, rows, formatter, empty_text):
        list_widget.clear()
        for row in rows:
            list_widget.addItem(formatter(row))
        if list_widget.count() == 0:
            list_widget.addItem(empty_text)

    def _get_recent_jobs(self):
        if self.repository is None:
            return []
        try:
            rows = self.repository.database.fetch_all(
                """
                SELECT job_type, title, status, error_message, created_at, finished_at
                FROM jobs
                ORDER BY COALESCE(NULLIF(finished_at, ''), created_at) DESC, id DESC
                LIMIT 15
                """
            )
            return [dict(row) for row in rows]
        except Exception:
            return []

    def _status_icon(self, video: dict) -> str:
        if int(video.get("is_downloaded") or 0):
            return "🟢"
        if int(video.get("is_members_only") or 0):
            return "🔵"
        if int(video.get("is_new") or 0):
            return "🟡"
        if (video.get("status") or "") == "error":
            return "🔴"
        return "⚪"

    def set_assistant_report(self, report: dict):
        score = int(report.get("score") or 0)
        self.assistant_score.setText(f"Health Score: {score} %")
        self.assistant_progress.setValue(score)
        self.assistant_headline.setText(report.get("headline") or "Keine Meldung")

        checks = report.get("checks", [])
        important = [c for c in checks if c.get("status") in ("error", "warn")]
        if not important:
            important = checks[:5]

        self.assistant_list.clear()
        for check in important[:6]:
            action = check.get("action") or ""
            suffix = f"  → {action}" if action else ""
            self.assistant_list.addItem(
                f"{check.get('icon', '⚪')} {check.get('area')} · {check.get('title')}: "
                f"{check.get('message')}{suffix}"
            )
        if self.assistant_list.count() == 0:
            self.assistant_list.addItem("🟢 Keine Empfehlungen.")

        self._update_notifications(report)

    def _update_notifications(self, report: dict):
        self.notifications_list.clear()
        checks = report.get("checks", [])
        notifications = [c for c in checks if c.get("status") in ("error", "warn")]
        for check in notifications[:8]:
            self.notifications_list.addItem(
                f"{check.get('icon', '⚪')} {check.get('title')}: {check.get('message')}"
            )
        if not notifications:
            self.notifications_list.addItem("🟢 Keine offenen Empfehlungen.")
