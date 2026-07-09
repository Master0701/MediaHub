from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush


class VideoSelectionDialog(QDialog):
    def __init__(self, videos, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Videos auswählen")
        self.resize(1150, 650)

        self.videos = self.remove_duplicates(videos)
        self.selected_videos = []

        layout = QVBoxLayout(self)

        self.title_label = QLabel("Wähle die Videos aus, die heruntergeladen werden sollen:")
        layout.addWidget(self.title_label)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Suchen:"))

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Titel, Playlist oder ID filtern...")
        self.search_box.textChanged.connect(self.apply_filter)

        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(False)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Auswahl", "Titel", "Playlist", "ID", "Status"])

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(self.update_status)

        layout.addWidget(self.table)

        button_row = QHBoxLayout()

        self.btn_all = QPushButton("Alle")
        self.btn_none = QPushButton("Keine")
        self.btn_new = QPushButton("Nur neue")
        self.btn_invert = QPushButton("Invertieren")
        self.btn_ok = QPushButton("Download starten")
        self.btn_cancel = QPushButton("Abbrechen")

        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)
        self.btn_new.clicked.connect(self.select_new)
        self.btn_invert.clicked.connect(self.invert_selection)
        self.btn_ok.clicked.connect(self.accept_selection)
        self.btn_cancel.clicked.connect(self.reject)

        button_row.addWidget(self.btn_all)
        button_row.addWidget(self.btn_none)
        button_row.addWidget(self.btn_new)
        button_row.addWidget(self.btn_invert)
        button_row.addStretch()
        button_row.addWidget(self.btn_ok)
        button_row.addWidget(self.btn_cancel)

        layout.addLayout(button_row)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.load_videos()


    def _apply_members_style(self, item: QTableWidgetItem):
        # Extra robust gegen dunkle Themes/Qt-Stylesheets.
        background = QBrush(QColor(170, 25, 25))
        foreground = QBrush(QColor(255, 255, 255))
        item.setBackground(background)
        item.setForeground(foreground)
        item.setData(Qt.ItemDataRole.BackgroundRole, background)
        item.setData(Qt.ItemDataRole.ForegroundRole, foreground)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setToolTip("🔒 Dieses Video ist nur für Kanalmitglieder/Abonnenten verfügbar.")

    def _is_members_only_video(self, video: dict) -> bool:
        if int(video.get("is_members_only") or 0) == 1:
            return True

        text = " ".join(
            str(video.get(key, ""))
            for key in ("title", "status", "availability", "error", "message")
        ).lower()
        markers = (
            "members-only", "members only", "member-only",
            "channel's members", "channel members", "join this channel",
            "kanalmitglied", "kanalmitgliedschaft", "kanal-abonnenten",
            "abo-video", "subscriber-only", "subscribers only",
            "premium_only", "premium only", "requires payment",
            "zur kanal unterstützung", "zur kanal unterstuetzung",
        )
        return any(marker in text for marker in markers)

    def _status_text(self, video: dict) -> str:
        status = str(video.get("status", "Neu") or "Neu")
        if self._is_members_only_video(video) or status.lower() in {"members_only", "member", "members"}:
            return "🔴 🔒 Mitglieder"
        return status

    def remove_duplicates(self, videos):
        unique_videos = []
        known_keys = set()

        for video in videos:
            video_id = video.get("id") or video.get("video_id", "")
            video_url = video.get("url", "")
            key = video_id or video_url

            if not key:
                unique_videos.append(video)
                continue

            if key in known_keys:
                continue

            known_keys.add(key)
            unique_videos.append(video)

        return unique_videos

    def load_videos(self):
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for video in self.videos:
            row = self.table.rowCount()
            self.table.insertRow(row)

            check_item = QTableWidgetItem()
            check_item.setFlags(check_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check_item.setCheckState(
                Qt.CheckState.Checked if video.get("checked", True) else Qt.CheckState.Unchecked
            )
            check_item.setData(Qt.ItemDataRole.UserRole, video)

            is_members = self._is_members_only_video(video)
            title_text = str(video.get("title", "Ohne Titel") or "Ohne Titel")
            if is_members and not title_text.startswith("🔒"):
                title_text = f"🔒 {title_text}"

            title_item = QTableWidgetItem(title_text)
            playlist_item = QTableWidgetItem(video.get("playlist", ""))
            id_item = QTableWidgetItem(video.get("id") or video.get("video_id", ""))
            status_item = QTableWidgetItem(self._status_text(video))

            items = [check_item, title_item, playlist_item, id_item, status_item]
            if is_members:
                for table_item in items:
                    self._apply_members_style(table_item)

            self.table.setItem(row, 0, check_item)
            self.table.setItem(row, 1, title_item)
            self.table.setItem(row, 2, playlist_item)
            self.table.setItem(row, 3, id_item)
            self.table.setItem(row, 4, status_item)

        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)
        self.update_status()

    def apply_filter(self):
        search = self.search_box.text().strip().lower()

        for row in range(self.table.rowCount()):
            title = self.get_text(row, 1).lower()
            playlist = self.get_text(row, 2).lower()
            video_id = self.get_text(row, 3).lower()

            visible = (
                search in title
                or search in playlist
                or search in video_id
            )

            self.table.setRowHidden(row, not visible)

        self.update_status()

    def select_all(self):
        self.table.blockSignals(True)

        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                self.table.item(row, 0).setCheckState(Qt.CheckState.Checked)

        self.table.blockSignals(False)
        self.update_status()

    def select_none(self):
        self.table.blockSignals(True)

        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                self.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)

        self.table.blockSignals(False)
        self.update_status()

    def select_new(self):
        self.table.blockSignals(True)

        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue

            status = self.get_text(row, 4)
            check_item = self.table.item(row, 0)

            if status == "Neu":
                check_item.setCheckState(Qt.CheckState.Checked)
            else:
                check_item.setCheckState(Qt.CheckState.Unchecked)

        self.table.blockSignals(False)
        self.update_status()

    def invert_selection(self):
        self.table.blockSignals(True)

        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue

            item = self.table.item(row, 0)

            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)

        self.table.blockSignals(False)
        self.update_status()

    def accept_selection(self):
        self.selected_videos = []

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)

            if item and item.checkState() == Qt.CheckState.Checked:
                video = item.data(Qt.ItemDataRole.UserRole)
                self.selected_videos.append(video)

        self.accept()

    def get_text(self, row, column):
        item = self.table.item(row, column)
        return item.text() if item else ""

    def update_status(self):
        visible_count = 0
        selected_count = 0
        new_count = 0
        loaded_count = 0
        members_count = 0
        playlist_names = set()

        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue

            visible_count += 1

            playlist = self.get_text(row, 2)
            if playlist:
                playlist_names.add(playlist)

            status = self.get_text(row, 4)

            if "Mitglieder" in status or "🔒" in status:
                members_count += 1
            elif status == "Neu":
                new_count += 1
            elif status == "Bereits geladen":
                loaded_count += 1

            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_count += 1

        playlist_text = f"{len(playlist_names)} Playlists | " if playlist_names else ""

        self.status_label.setText(
            f"{selected_count} ausgewählt | "
            f"{new_count} neu | "
            f"{loaded_count} bereits geladen | "
            f"🔴 🔒 {members_count} Mitglieder | "
            f"{playlist_text}"
            f"{visible_count} sichtbar | "
            f"{len(self.videos)} insgesamt"
        )