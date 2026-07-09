from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QSpinBox,
    QWidget,
    QHBoxLayout,
)
from PySide6.QtCore import Qt


class PlaylistTable(QTableWidget):
    COL_IMPORT = 0
    COL_YOUTUBE_NAME = 1
    COL_DISPLAY_NAME = 2
    COL_SEASON = 3

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setColumnCount(4)
        self.setHorizontalHeaderLabels([
            "Import",
            "YouTube-Name",
            "Plex-Name",
            "Staffel",
        ])

        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self.horizontalHeader().setStretchLastSection(False)
        self.setColumnWidth(self.COL_IMPORT, 70)
        self.setColumnWidth(self.COL_YOUTUBE_NAME, 220)
        self.setColumnWidth(self.COL_DISPLAY_NAME, 220)
        self.setColumnWidth(self.COL_SEASON, 80)

    def set_playlists(self, playlists):
        self.setRowCount(0)

        if not playlists:
            return

        for row, playlist in enumerate(playlists):
            self.insertRow(row)

            # Teil 9 Fix 5:
            # Der Assistent bekommt nach sync_playlist_settings() keine "title"-Liste mehr,
            # sondern Settings mit "playlist_name". Vorher wurde deshalb in der
            # YouTube-Name-Spalte immer der Fallback "Ohne Titel" angezeigt,
            # obwohl der richtige Name schon im Plex-Namen stand.
            title = (
                playlist.get("title")
                or playlist.get("playlist_name")
                or playlist.get("name")
                or "Ohne Titel"
            )
            title = str(title or "Ohne Titel").strip() or "Ohne Titel"

            display_name = (
                playlist.get("display_name")
                or playlist.get("plex_name")
                or title
            )
            display_name = str(display_name or title).strip() or title

            # Wichtig: Daten normalisieren, damit spätere Funktionen wieder überall
            # denselben Titel finden und nicht erneut auf "Ohne Titel" fallen.
            playlist = dict(playlist)
            playlist["title"] = title
            playlist["playlist_name"] = title
            playlist["display_name"] = display_name

            season = int(playlist.get("season", row + 1) or row + 1)
            enabled = bool(playlist.get("enabled", True))

            checkbox = QCheckBox()
            checkbox.setChecked(enabled)

            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.addWidget(checkbox)

            youtube_item = QTableWidgetItem(title)
            youtube_item.setFlags(youtube_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            youtube_item.setData(Qt.ItemDataRole.UserRole, playlist)

            display_item = QTableWidgetItem(display_name)

            season_box = QSpinBox()
            season_box.setRange(1, 999)
            season_box.setValue(season)

            self.setCellWidget(row, self.COL_IMPORT, checkbox_container)
            self.setItem(row, self.COL_YOUTUBE_NAME, youtube_item)
            self.setItem(row, self.COL_DISPLAY_NAME, display_item)
            self.setCellWidget(row, self.COL_SEASON, season_box)

    def get_playlist_settings(self):
        settings = []

        for row in range(self.rowCount()):
            youtube_item = self.item(row, self.COL_YOUTUBE_NAME)
            display_item = self.item(row, self.COL_DISPLAY_NAME)

            if youtube_item is None:
                continue

            playlist = youtube_item.data(Qt.ItemDataRole.UserRole) or {}

            checkbox_container = self.cellWidget(row, self.COL_IMPORT)
            checkbox = checkbox_container.findChild(QCheckBox) if checkbox_container else None

            season_box = self.cellWidget(row, self.COL_SEASON)

            playlist_name = (
                playlist.get("title")
                or playlist.get("playlist_name")
                or youtube_item.text()
                or "Ohne Titel"
            )
            playlist_name = str(playlist_name or "Ohne Titel").strip() or "Ohne Titel"
            display_name = display_item.text().strip() if display_item else playlist_name
            display_name = display_name or playlist_name

            settings.append({
                "playlist_id": playlist.get("id", playlist.get("playlist_id", "")),
                "playlist_name": playlist_name,
                "title": playlist_name,
                "display_name": display_name,
                "season": int(season_box.value()) if season_box else row + 1,
                "enabled": bool(checkbox.isChecked()) if checkbox else True,
                "url": playlist.get("url", ""),
                "thumbnail_url": playlist.get("thumbnail_url", playlist.get("thumbnail", "")),
                "thumbnail": playlist.get("thumbnail", playlist.get("thumbnail_url", "")),
                "image_path": playlist.get("image_path", ""),
            })

        return settings

    def get_selected_playlists(self):
        selected = []

        for row in range(self.rowCount()):
            youtube_item = self.item(row, self.COL_YOUTUBE_NAME)

            if youtube_item is None:
                continue

            playlist = youtube_item.data(Qt.ItemDataRole.UserRole) or {}

            checkbox_container = self.cellWidget(row, self.COL_IMPORT)
            checkbox = checkbox_container.findChild(QCheckBox) if checkbox_container else None

            if checkbox and not checkbox.isChecked():
                continue

            display_item = self.item(row, self.COL_DISPLAY_NAME)
            season_box = self.cellWidget(row, self.COL_SEASON)

            title = (
                playlist.get("title")
                or playlist.get("playlist_name")
                or youtube_item.text()
                or "Ohne Titel"
            )
            title = str(title or "Ohne Titel").strip() or "Ohne Titel"

            prepared = dict(playlist)
            prepared["title"] = title
            prepared["playlist_name"] = title
            prepared["display_name"] = display_item.text().strip() if display_item else playlist.get("display_name", title)
            prepared["display_name"] = prepared["display_name"] or title
            prepared["season"] = int(season_box.value()) if season_box else row + 1
            prepared["enabled"] = True

            selected.append(prepared)

        return selected

