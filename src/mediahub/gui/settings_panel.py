from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QCheckBox,
    QTabWidget, QSizePolicy
)

from src.mediahub.services.profile_service import ProfileService


class SettingsPanel(QWidget):
    PLAYLIST_FOLDER_MODES = [
        "Nur Staffeln",
        "Playlist → Staffel",
        "Playlist ohne Staffel",
        "Staffel = Playlist",
    ]

    def __init__(self):
        super().__init__()

        self.channel = None
        self.change_callback = None
        self._loading = False

        # Das rechte Einstellungsfenster darf schmal werden, ohne den
        # Kanalbereich wieder zusammenzudrücken.
        self.setMinimumWidth(250)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Expanding,
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(0)
        self.tabs.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Expanding,
        )
        outer_layout.addWidget(self.tabs)

        self.tab_general = QWidget()
        self.tab_download = QWidget()
        self.tab_plex = QWidget()
        self.tab_artwork = QWidget()

        self.tabs.addTab(self.tab_general, "Allgemein")
        self.tabs.addTab(self.tab_download, "Download")
        self.tabs.addTab(self.tab_plex, "Plex")
        self.tabs.addTab(self.tab_artwork, "Artwork")

        self.build_general_tab()
        self.build_download_tab()
        self.build_plex_tab()
        self.build_artwork_tab()

    def build_general_tab(self):
        layout = QVBoxLayout(self.tab_general)

        self.lbl_name = QLabel("Kanal: -")
        self.lbl_url = QLabel("URL: -")
        self.lbl_work = QLabel("Arbeitsordner: -")
        self.lbl_target = QLabel("Plex-Ziel: -")

        for label in (
            self.lbl_name,
            self.lbl_url,
            self.lbl_work,
            self.lbl_target,
        ):
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred,
            )

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.lbl_url)
        layout.addWidget(self.lbl_work)
        layout.addWidget(self.lbl_target)
        layout.addStretch()

    def build_download_tab(self):
        layout = QVBoxLayout(self.tab_download)

        layout.addWidget(QLabel("Download-Profil"))
        self.profile = QComboBox()
        self.profile.addItems(ProfileService.names())
        layout.addWidget(self.profile)

        self.audio_only = QCheckBox("Nur Audio herunterladen")
        layout.addWidget(self.audio_only)

        layout.addWidget(QLabel("Container"))
        self.container = QComboBox()
        self.container.addItems(["MKV", "MP4", "WebM"])
        layout.addWidget(self.container)

        layout.addWidget(QLabel("Auflösung"))
        self.resolution = QComboBox()
        self.resolution.addItems(["Beste", "4K", "1440p", "1080p", "720p", "480p"])
        layout.addWidget(self.resolution)

        layout.addWidget(QLabel("Audioformat"))
        self.audio = QComboBox()
        self.audio.addItems(["M4A", "MP3", "AAC", "FLAC", "OGG", "WAV"])
        layout.addWidget(self.audio)

        self.clean_work = QCheckBox("Arbeitsordner nach Import leeren")
        layout.addWidget(self.clean_work)

        layout.addStretch()

        self.profile.currentTextChanged.connect(self._profile_changed)
        self.audio_only.stateChanged.connect(self._notify_change)
        self.container.currentTextChanged.connect(self._notify_change)
        self.resolution.currentTextChanged.connect(self._notify_change)
        self.audio.currentTextChanged.connect(self._notify_change)
        self.clean_work.stateChanged.connect(self._notify_change)

    def build_plex_tab(self):
        layout = QVBoxLayout(self.tab_plex)

        self.create_nfo = QCheckBox("NFO erzeugen")
        self.create_poster = QCheckBox("Poster erzeugen")
        self.create_fanart = QCheckBox("Fanart erzeugen")

        layout.addWidget(self.create_nfo)
        layout.addWidget(self.create_poster)
        layout.addWidget(self.create_fanart)

        layout.addWidget(QLabel("Ablage-Modus für Playlists"))
        self.playlist_folder_mode = QComboBox()
        self.playlist_folder_mode.addItems(self.PLAYLIST_FOLDER_MODES)
        layout.addWidget(self.playlist_folder_mode)

        self.playlist_mode_info = QLabel("")
        self.playlist_mode_info.setWordWrap(True)
        layout.addWidget(self.playlist_mode_info)

        layout.addStretch()

        self.create_nfo.stateChanged.connect(self._notify_change)
        self.create_poster.stateChanged.connect(self._notify_change)
        self.create_fanart.stateChanged.connect(self._notify_change)
        self.playlist_folder_mode.currentTextChanged.connect(self.update_playlist_mode_info)
        self.playlist_folder_mode.currentTextChanged.connect(self._notify_change)

        self.update_playlist_mode_info()

    def build_artwork_tab(self):
        layout = QVBoxLayout(self.tab_artwork)

        self.poster_preview = QLabel("Kein Poster")
        self.poster_preview.setFixedHeight(180)
        self.poster_preview.setStyleSheet("border: 1px solid #555; background-color: #2B2B2B;")
        self.poster_preview.setScaledContents(True)

        self.fanart_preview = QLabel("Keine Fanart")
        self.fanart_preview.setFixedHeight(140)
        self.fanart_preview.setStyleSheet("border: 1px solid #555; background-color: #2B2B2B;")
        self.fanart_preview.setScaledContents(True)

        self.poster_path = QLabel("Poster: automatisch")
        self.fanart_path = QLabel("Fanart: automatisch")
        self.poster_path.setWordWrap(True)
        self.fanart_path.setWordWrap(True)
        self.poster_path.setMinimumWidth(0)
        self.fanart_path.setMinimumWidth(0)

        layout.addWidget(QLabel("Poster"))
        layout.addWidget(self.poster_preview)
        layout.addWidget(self.poster_path)

        layout.addWidget(QLabel("Fanart"))
        layout.addWidget(self.fanart_preview)
        layout.addWidget(self.fanart_path)

        layout.addStretch()

    def load_channel(self, channel):
        self.channel = channel
        self._loading = True

        if channel is None:
            self.setEnabled(False)
            self._loading = False
            return

        self.setEnabled(True)

        self.lbl_name.setText(f"Kanal: {channel.name}")
        self.lbl_url.setText(f"URL: {channel.url or 'nicht gesetzt'}")
        self.lbl_work.setText(f"Arbeitsordner: {channel.work_folder or 'nicht gesetzt'}")
        self.lbl_target.setText(f"Plex-Ziel: {channel.target_folder or 'nicht gesetzt'}")

        self.profile.setCurrentText(channel.profile)
        self.audio_only.setChecked(channel.audio_only)

        self.container.setCurrentText(channel.container)
        self.resolution.setCurrentText(channel.resolution)
        self.audio.setCurrentText(channel.audio_format)

        self.create_nfo.setChecked(channel.create_nfo)
        self.create_poster.setChecked(channel.create_poster)
        self.create_fanart.setChecked(channel.create_fanart)
        self.clean_work.setChecked(channel.clean_work_folder)

        playlist_mode = getattr(channel, "playlist_folder_mode", "Nur Staffeln")

        if playlist_mode == "Playlist-Ordner + Staffeln":
            playlist_mode = "Playlist → Staffel"

        if playlist_mode not in self.PLAYLIST_FOLDER_MODES:
            playlist_mode = "Nur Staffeln"

        self.playlist_folder_mode.setCurrentText(playlist_mode)
        self.update_playlist_mode_info(playlist_mode)

        self.update_artwork_preview(channel)

        self._loading = False

    def _profile_changed(self, profile_name):
        if self._loading or self.channel is None:
            return

        profile = ProfileService.get(profile_name)

        self._loading = True

        self.audio_only.setChecked(profile["audio_only"])
        self.container.setCurrentText(profile["container"])
        self.resolution.setCurrentText(profile["resolution"])
        self.audio.setCurrentText(profile["audio_format"])
        self.create_nfo.setChecked(profile["create_nfo"])
        self.create_poster.setChecked(profile["create_poster"])
        self.create_fanart.setChecked(profile["create_fanart"])

        self._loading = False
        self._notify_change()

    def update_playlist_mode_info(self, mode=None):
        if mode is None:
            mode = self.playlist_folder_mode.currentText()

        examples = {
            "Nur Staffeln": "Ablage: Kanal / Season 01 / Video",
            "Playlist → Staffel": "Ablage: Kanal / Playlistname / Season 01 / Video",
            "Playlist ohne Staffel": "Ablage: Kanal / Playlistname / Video",
            "Staffel = Playlist": "Ablage: Kanal / Season 01 - Playlistname / Video",
        }

        self.playlist_mode_info.setText(examples.get(mode, ""))

    def update_artwork_preview(self, channel):
        self.poster_path.setText(f"Poster: {channel.poster or 'automatisch'}")
        self.fanart_path.setText(f"Fanart: {channel.fanart or 'automatisch'}")

        self.set_preview(self.poster_preview, channel.poster, "Kein Poster")
        self.set_preview(self.fanart_preview, channel.fanart, "Keine Fanart")

    def set_preview(self, label, path, fallback_text):
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            label.setPixmap(pixmap)
            label.setText("")
        else:
            label.setPixmap(QPixmap())
            label.setText(fallback_text)

    def _notify_change(self):
        if self._loading or self.channel is None:
            return

        if self.change_callback:
            self.change_callback(
                profile=self.profile.currentText(),
                audio_only=self.audio_only.isChecked(),
                container=self.container.currentText(),
                resolution=self.resolution.currentText(),
                audio_format=self.audio.currentText(),
                create_nfo=self.create_nfo.isChecked(),
                create_poster=self.create_poster.isChecked(),
                create_fanart=self.create_fanart.isChecked(),
                clean_work_folder=self.clean_work.isChecked(),
                playlist_folder_mode=self.playlist_folder_mode.currentText(),
            )