from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QListWidget, QSplitter,
    QScrollArea
)


class StatisticsPanel(QWidget):
    """Statistik-Center für MediaHub.

    Die Seite liest nur aus Repository/SQLite und verändert keine Daten.
    Dadurch bleibt sie sicher für bestehende rc6-Projekte.
    """

    def __init__(self, repository=None, parent=None):
        super().__init__(parent)
        self.repository = repository

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("📈 Statistik-Center")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.subtitle = QLabel("Auswertung aus SQLite und Download-Ordnern")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.subtitle)
        header.addWidget(self.btn_refresh)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._build_overview()
        self._build_today_week_month()
        self._build_lists()
        self._build_bars()

        self.refresh()

    def _build_overview(self):
        box = QGroupBox("Gesamtübersicht")
        grid = QGridLayout(box)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        self.overview_labels = {}
        items = [
            ("channels", "Kanäle"),
            ("playlists", "Playlists"),
            ("videos", "Videos"),
            ("downloaded_videos", "Downloads gesamt"),
            ("new_videos", "Neue Videos"),
            ("members_only_videos", "Mitglieder-Videos"),
            ("download_success_rate", "Downloadquote"),
            ("error_rate", "Fehlerquote"),
            ("avg_duration", "Ø Videolänge"),
            ("db_size", "Datenbankgröße"),
            ("download_folder_size", "Downloadordner"),
            ("last_sync", "Letzte Sync"),
        ]
        for index, (key, label_text) in enumerate(items):
            row = index // 4
            col = (index % 4) * 2
            label = QLabel(label_text + ":")
            value = QLabel("-")
            value.setStyleSheet("font-weight: bold;")
            grid.addWidget(label, row, col)
            grid.addWidget(value, row, col + 1)
            self.overview_labels[key] = value

        self.content_layout.addWidget(box)

    def _build_today_week_month(self):
        box = QGroupBox("Zeiträume")
        grid = QGridLayout(box)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        self.period_labels = {}
        items = [
            ("downloads_today", "Downloads heute"),
            ("downloads_week", "Downloads diese Woche"),
            ("downloads_month", "Downloads diesen Monat"),
            ("new_today", "Neue Videos heute"),
            ("new_week", "Neue Videos diese Woche"),
            ("new_month", "Neue Videos diesen Monat"),
            ("jobs_active", "Jobs aktiv"),
            ("jobs_failed", "Jobs Fehler"),
        ]
        for index, (key, label_text) in enumerate(items):
            row = index // 4
            col = (index % 4) * 2
            label = QLabel(label_text + ":")
            value = QLabel("-")
            value.setStyleSheet("font-weight: bold;")
            grid.addWidget(label, row, col)
            grid.addWidget(value, row, col + 1)
            self.period_labels[key] = value

        self.content_layout.addWidget(box)

    def _build_lists(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        self.top_channels_list = self._make_list_box(splitter, "Größte Kanäle")
        self.top_playlists_list = self._make_list_box(splitter, "Größte Playlists")
        self.recent_downloads_list = self._make_list_box(splitter, "Letzte Downloads")

        splitter.setSizes([360, 360, 360])
        self.content_layout.addWidget(splitter, 1)

    def _build_bars(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        self.downloads_by_day_list = self._make_list_box(splitter, "Downloads pro Tag")
        self.new_by_week_list = self._make_list_box(splitter, "Neue Videos pro Woche")

        splitter.setSizes([540, 540])
        self.content_layout.addWidget(splitter, 1)

    def _make_list_box(self, parent, title):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        parent.addWidget(box)
        return list_widget

    def refresh(self):
        if self.repository is None:
            self.subtitle.setText("Keine Datenbank verfügbar")
            return

        stats = self.repository.get_statistics_summary()
        overview = stats.get("overview", {})
        periods = stats.get("periods", {})

        for key, label in self.overview_labels.items():
            label.setText(str(overview.get(key, "-") or "-"))
        for key, label in self.period_labels.items():
            label.setText(str(periods.get(key, "-") or "-"))

        self._fill_list(
            self.top_channels_list,
            stats.get("top_channels", []),
            lambda row: f"📺 {row.get('name') or 'Unbekannt'} — {row.get('video_count', 0)} Videos, {row.get('downloaded_count', 0)} geladen",
            "Noch keine Kanaldaten."
        )
        self._fill_list(
            self.top_playlists_list,
            stats.get("top_playlists", []),
            lambda row: f"📂 {row.get('title') or 'Unbekannt'} — {row.get('video_count', 0)} Videos",
            "Noch keine Playlistdaten."
        )
        self._fill_list(
            self.recent_downloads_list,
            stats.get("recent_downloads", []),
            lambda row: f"⬇ {row.get('title') or row.get('filename') or row.get('video_id') or 'Unbekannt'} — {row.get('channel_name') or 'Unbekannt'}",
            "Noch keine Downloads."
        )
        self._fill_list(
            self.downloads_by_day_list,
            stats.get("downloads_by_day", []),
            lambda row: self._bar_line(row.get('day') or '-', int(row.get('count') or 0), stats.get('max_downloads_by_day', 1)),
            "Noch keine Tagesdaten."
        )
        self._fill_list(
            self.new_by_week_list,
            stats.get("new_by_week", []),
            lambda row: self._bar_line(row.get('week') or '-', int(row.get('count') or 0), stats.get('max_new_by_week', 1)),
            "Noch keine Wochendaten."
        )

    def _fill_list(self, list_widget, rows, formatter, empty_text):
        list_widget.clear()
        for row in rows:
            list_widget.addItem(formatter(row))
        if list_widget.count() == 0:
            list_widget.addItem(empty_text)

    def _bar_line(self, label, value, maximum):
        maximum = max(int(maximum or 1), 1)
        width = max(1, round((value / maximum) * 18)) if value else 0
        bar = "█" * width if width else "·"
        return f"{label}  {bar}  {value}"
