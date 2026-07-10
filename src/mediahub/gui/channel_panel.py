from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QGroupBox, QMessageBox, QSizePolicy, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt

from src.mediahub.models.channel import Channel
from src.mediahub.gui.channel_editor import ChannelEditor
from src.mediahub.gui.channel_wizard import ChannelWizard


class ChannelPanel(QWidget):
    def __init__(self, controller, repository=None):
        super().__init__()

        self.controller = controller
        self.repository = repository
        self.channel_selected_callback = None

        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        left_box = QGroupBox("📺 Kanäle")
        left_box.setMinimumWidth(220)
        left_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(6, 10, 6, 6)
        left_layout.setSpacing(6)

        self.channel_list = QListWidget()
        self.channel_list.setMinimumWidth(190)
        self.channel_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.channel_list.currentRowChanged.connect(self.on_channel_selected)

        self.btn_add = QPushButton("+")
        self.btn_add.setToolTip("Kanal hinzufügen")

        self.btn_assistant = QPushButton("Assistent")
        self.btn_assistant.setToolTip("Kanal-Assistent")

        self.btn_edit = QPushButton("Bearbeiten")
        self.btn_edit.setToolTip("Kanal bearbeiten")

        self.btn_remove = QPushButton("-")
        self.btn_remove.setToolTip("Kanal entfernen")

        self.btn_add.clicked.connect(self.add_channel)
        self.btn_assistant.clicked.connect(self.add_channel_with_assistant)
        self.btn_edit.clicked.connect(self.edit_channel)
        self.btn_remove.clicked.connect(self.remove_channel)

        button_row = QHBoxLayout()
        button_row.addWidget(self.btn_add)
        button_row.addWidget(self.btn_assistant)
        button_row.addWidget(self.btn_edit)
        button_row.addWidget(self.btn_remove)

        left_layout.addWidget(self.channel_list)
        left_layout.addLayout(button_row)

        center_box = QGroupBox("Kanal")
        center_box.setMinimumWidth(0)
        center_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        center_layout = QVBoxLayout(center_box)
        center_layout.setContentsMargins(8, 10, 8, 8)
        center_layout.setSpacing(8)

        self.title = QLabel("")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.title.setMinimumWidth(0)

        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setMinimumWidth(0)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info.setStyleSheet(
            "QLabel {"
            "font-size: 11px;"
            "padding: 2px 4px;"
            "}"
        )

        self.info_scroll = QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.info_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.info_scroll.setMinimumHeight(180)
        self.info_scroll.setWidget(self.info)

        self.status_info = QLabel("Noch keine Datenbank-Statistik vorhanden.")
        self.status_info.setWordWrap(True)
        self.status_info.setMinimumWidth(0)
        self.status_info.setStyleSheet(
            "QLabel {"
            "background-color: rgba(255, 255, 255, 0.05);"
            "border: 1px solid rgba(255, 255, 255, 0.12);"
            "border-radius: 6px;"
            "padding: 8px;"
            "}"
        )

        self.btn_preview = QPushButton("Vorschau")
        self.btn_download = QPushButton("Download")

        center_layout.addWidget(self.title)
        center_layout.addWidget(self.info_scroll, 1)
        center_layout.addWidget(self.status_info)
        center_layout.addStretch()
        center_layout.addWidget(self.btn_preview)
        center_layout.addWidget(self.btn_download)

        self.inner_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.inner_splitter.setChildrenCollapsible(False)
        self.inner_splitter.addWidget(left_box)
        self.inner_splitter.addWidget(center_box)
        # Linke Kanalseite etwas breiter, rechte Detailseite etwas schmaler.
        self.inner_splitter.setSizes([430, 450])
        self.inner_splitter.setStretchFactor(0, 3)
        self.inner_splitter.setStretchFactor(1, 2)

        layout.addWidget(self.inner_splitter)

        self.refresh_list()

    def refresh_list(self):
        self.channel_list.blockSignals(True)
        self.channel_list.clear()

        for channel in self.controller.get_channels():
            playlist_count = len(getattr(channel, "playlist_settings", []) or [])
            active_count = self.count_active_playlists(channel)

            if playlist_count:
                self.channel_list.addItem(
                    f"{channel.name} ({active_count}/{playlist_count})"
                )
            else:
                self.channel_list.addItem(channel.name)

        self.channel_list.blockSignals(False)

        if self.controller.get_channels():
            index = self.controller.current_index
            if index < 0:
                index = 0

            self.channel_list.setCurrentRow(index)
            self.on_channel_selected(index)
        else:
            self.on_channel_selected(-1)

    def on_channel_selected(self, row: int):
        channel = self.controller.set_current_index(row)

        if channel is None:
            self.title.setText("")
            self.info.setText("Kein Kanal ausgewählt.")
            self.status_info.setText("Keine Statistik verfügbar.")

            if self.channel_selected_callback:
                self.channel_selected_callback(None)

            return

        playlist_count = len(getattr(channel, "playlist_settings", []) or [])
        active_count = self.count_active_playlists(channel)
        playlist_mode = getattr(channel, "playlist_folder_mode", "Nur Staffeln")

        self.title.setText(channel.name)
        self.info.setText(
            f"🌐 URL\n{channel.url or 'nicht gesetzt'}\n\n"
            f"📁 Arbeitsordner\n{channel.work_folder or 'nicht gesetzt'}\n\n"
            f"🎬 Plex-Ziel\n{channel.target_folder or 'nicht gesetzt'}\n\n"
            f"📂 Playlist-Ablage\n{playlist_mode}\n\n"
            f"📋 Playlists\n{active_count} aktiv / {playlist_count} gespeichert\n\n"
            f"🖼 Poster\n{channel.poster or 'automatisch'}\n\n"
            f"🌄 Fanart\n{channel.fanart or 'automatisch'}\n\n"
            f"⚙️ Downloadprofil\n"
            f"Container: {channel.container}\n"
            f"Auflösung: {channel.resolution}\n"
            f"Audio: {channel.audio_format}"
        )
        self.update_channel_status(channel)

        if self.channel_selected_callback:
            self.channel_selected_callback(channel)


    def update_channel_status(self, channel=None):
        if channel is None:
            channel = self.controller.get_current_channel()

        if channel is None:
            self.status_info.setText("Keine Statistik verfügbar.")
            return

        if self.repository is None:
            self.status_info.setText("Datenbank-Status: noch nicht verbunden.")
            return

        try:
            stats = self.repository.get_channel_video_stats(channel.name)
        except Exception as error:
            self.status_info.setText(f"Datenbank-Status konnte nicht geladen werden: {error}")
            return

        last_sync = stats.get("last_checked_at") or "noch nie"
        self.status_info.setText(
            "Datenbank-Status\n"
            "────────────────────\n"
            f"Playlists: {stats.get('playlists', 0)}\n"
            f"Videos: {stats.get('videos', 0)}\n"
            f"Neu: {stats.get('new_videos', 0)}\n"
            f"Geladen: {stats.get('downloaded_videos', 0)}\n"
            f"Mitglieder: {stats.get('members_only_videos', 0)}\n"
            f"Letzte Sync: {last_sync}"
        )

    def count_active_playlists(self, channel):
        settings = getattr(channel, "playlist_settings", []) or []
        return sum(1 for setting in settings if setting.get("enabled", True))

    def update_current_info(self):
        self.on_channel_selected(self.channel_list.currentRow())

    def add_channel(self):
        channel = Channel(name="Neuer Kanal", url="")
        dialog = ChannelEditor(channel, self)

        if dialog.exec():
            dialog.apply_to_channel(channel)

            index = self.controller.add_channel(channel)

            self.refresh_list()
            self.channel_list.setCurrentRow(index)

    def add_channel_with_assistant(self):
        wizard = ChannelWizard(
            controller=self.controller,
            parent=self
        )

        if wizard.exec():
            self.refresh_list()

            if hasattr(wizard, "created_index"):
                self.channel_list.setCurrentRow(wizard.created_index)

    def edit_channel(self):
        row = self.channel_list.currentRow()
        current_channel = self.controller.get_current_channel()

        if current_channel is None:
            return

        edited_channel = Channel.from_dict(current_channel.to_dict())
        dialog = ChannelEditor(edited_channel, self)

        if dialog.exec():
            dialog.apply_to_channel(edited_channel)

            self.controller.update_channel(row, edited_channel)

            self.refresh_list()
            self.channel_list.setCurrentRow(row)

    def remove_channel(self):
        row = self.channel_list.currentRow()
        channel = self.controller.get_current_channel()

        if channel is None:
            return

        answer = QMessageBox.question(
            self,
            "Kanal löschen",
            f"Möchtest du den Kanal wirklich löschen?\n\n{channel.name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.controller.remove_channel(row)
        self.refresh_list()