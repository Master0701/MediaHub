from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QSpinBox
)
from PySide6.QtCore import Qt


class PlaylistManagerDialog(QDialog):
    def __init__(self, channel, playlists, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Playlist-Manager")
        self.resize(1000, 600)

        self.channel = channel
        self.playlists = playlists
        self.playlist_settings = self.merge_playlist_settings(
            playlists,
            getattr(channel, "playlist_settings", [])
        )

        layout = QVBoxLayout(self)

        self.title_label = QLabel(f"Playlist-Manager für: {channel.name}")
        layout.addWidget(self.title_label)

        self.info_label = QLabel(
            "Hier kannst du festlegen, welche Playlists aktiv sind, "
            "wie sie in Plex heißen und welche Staffel sie bekommen."
        )
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Aktiv",
            "YouTube-Playlist",
            "Plex-Name",
            "Staffel",
            "Videos",
            "Playlist-ID",
        ])

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)

        button_row = QHBoxLayout()

        self.btn_all = QPushButton("Alle aktiv")
        self.btn_none = QPushButton("Alle inaktiv")
        self.btn_auto_seasons = QPushButton("Staffeln automatisch")
        self.btn_ok = QPushButton("Speichern")
        self.btn_cancel = QPushButton("Abbrechen")

        self.btn_all.clicked.connect(self.enable_all)
        self.btn_none.clicked.connect(self.disable_all)
        self.btn_auto_seasons.clicked.connect(self.auto_seasons)
        self.btn_ok.clicked.connect(self.accept_selection)
        self.btn_cancel.clicked.connect(self.reject)

        button_row.addWidget(self.btn_all)
        button_row.addWidget(self.btn_none)
        button_row.addWidget(self.btn_auto_seasons)
        button_row.addStretch()
        button_row.addWidget(self.btn_ok)
        button_row.addWidget(self.btn_cancel)

        layout.addLayout(button_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.load_table()

    def merge_playlist_settings(self, playlists, old_settings):
        old_by_id = {}

        for setting in old_settings or []:
            playlist_id = setting.get("playlist_id", "")
            if playlist_id:
                old_by_id[playlist_id] = setting

        merged = []

        for index, playlist in enumerate(playlists, start=1):
            playlist_id = playlist.get("id", "")
            playlist_name = playlist.get("title", "Ohne Titel")

            old = old_by_id.get(playlist_id, {})

            merged.append({
                "playlist_id": playlist_id,
                "playlist_name": playlist_name,
                "display_name": old.get("display_name", playlist_name),
                "season": int(old.get("season", index)),
                "enabled": bool(old.get("enabled", True)),
                "url": playlist.get("url", old.get("url", "")),
                "video_count": int(old.get("video_count", playlist.get("video_count", playlist.get("playlist_count", 0)) or 0)),
                "sort_order": int(old.get("sort_order", index) or index),
            })

        return merged

    def load_table(self):
        self.table.setRowCount(0)

        for setting in self.playlist_settings:
            row = self.table.rowCount()
            self.table.insertRow(row)

            active_item = QTableWidgetItem()
            active_item.setFlags(active_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            active_item.setCheckState(
                Qt.CheckState.Checked if setting.get("enabled", True)
                else Qt.CheckState.Unchecked
            )

            playlist_item = QTableWidgetItem(setting.get("playlist_name", "Ohne Titel"))

            display_item = QTableWidgetItem(setting.get("display_name", setting.get("playlist_name", "")))

            season_spin = QSpinBox()
            season_spin.setMinimum(0)
            season_spin.setMaximum(999)
            season_spin.setValue(int(setting.get("season", row + 1)))

            video_count = int(setting.get("video_count", 0) or 0)
            count_text = str(video_count) if video_count > 0 else "-"
            count_item = QTableWidgetItem(count_text)
            count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            id_item = QTableWidgetItem(setting.get("playlist_id", ""))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table.setItem(row, 0, active_item)
            self.table.setItem(row, 1, playlist_item)
            self.table.setItem(row, 2, display_item)
            self.table.setCellWidget(row, 3, season_spin)
            self.table.setItem(row, 4, count_item)
            self.table.setItem(row, 5, id_item)

        self.update_status()

    def enable_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Checked)

        self.update_status()

    def disable_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)

        self.update_status()

    def auto_seasons(self):
        season = 1

        for row in range(self.table.rowCount()):
            spin = self.table.cellWidget(row, 3)
            if spin:
                spin.setValue(season)
                season += 1

        self.update_status()

    def accept_selection(self):
        new_settings = []

        for row in range(self.table.rowCount()):
            active_item = self.table.item(row, 0)
            playlist_item = self.table.item(row, 1)
            display_item = self.table.item(row, 2)
            season_spin = self.table.cellWidget(row, 3)
            count_item = self.table.item(row, 4)
            id_item = self.table.item(row, 5)

            playlist_name = playlist_item.text() if playlist_item else "Ohne Titel"
            display_name = display_item.text().strip() if display_item else playlist_name

            if not display_name:
                display_name = playlist_name

            new_settings.append({
                "playlist_id": id_item.text() if id_item else "",
                "playlist_name": playlist_name,
                "display_name": display_name,
                "season": season_spin.value() if season_spin else row + 1,
                "enabled": active_item.checkState() == Qt.CheckState.Checked if active_item else True,
                "url": self.playlist_settings[row].get("url", "") if row < len(self.playlist_settings) else "",
                "video_count": int(count_item.text()) if count_item and count_item.text().isdigit() else 0,
                "sort_order": row + 1,
            })

        self.playlist_settings = new_settings
        self.accept()

    def update_status(self):
        total = self.table.rowCount()
        active = 0

        for row in range(total):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                active += 1

        self.status_label.setText(f"{active} aktiv | {total} Playlists insgesamt")