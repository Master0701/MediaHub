import re
from urllib.parse import urlparse, unquote

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QSplitter, QWidget
)
from PySide6.QtCore import Qt, QTimer

from src.mediahub.models.channel import Channel
from src.mediahub.services.youtube_service import YouTubeService
from src.mediahub.services.playlist_service import PlaylistService
from src.mediahub.services.image_manager import ImageAssetManager

from src.mediahub.gui.channel_wizard_parts.info_panel import ChannelWizardInfoPanel
from src.mediahub.gui.channel_wizard_parts.progress_panel import ChannelWizardProgressPanel
from src.mediahub.gui.channel_wizard_parts.playlist_panel import ChannelWizardPlaylistPanel


class ChannelWizard(QDialog):
    def __init__(self, controller, youtube_service=None, playlist_service=None, parent=None):
        super().__init__(parent)

        self.controller = controller
        self.youtube_service = youtube_service or YouTubeService()
        self.playlist_service = playlist_service or PlaylistService(self.youtube_service)
        self.image_manager = ImageAssetManager()

        self.created_channel = None
        self.created_index = None

        self.url = ""
        self.detected_name = ""
        self.channel_info = {}
        self.playlists = []

        self.step_index = 0
        self.ready_to_save = False

        self.steps = [
            "Kanal-URL prüfen",
            "Kanal auf YouTube finden",
            "Kanalname lesen",
            "Avatar vorbereiten",
            "Banner vorbereiten",
            "Beschreibung lesen",
            "Playlists lesen",
            "Kanal anlegen",
            "Playlist-Einstellungen speichern",
        ]

        self.setWindowTitle("Kanal-Assistent")
        self.resize(900, 620)
        self.setMinimumSize(700, 500)

        self.build_ui()

    def build_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("Kanal-Assistent")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")

        subtitle = QLabel("YouTube-Kanal automatisch einrichten")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText(
            "YouTube-Kanal-URL einfügen, z. B.\n"
            "https://youtube.com/@Tom-Micro-Soldering"
        )
        self.url_input.setFixedHeight(70)

        self.info_panel = ChannelWizardInfoPanel()
        self.progress_panel = ChannelWizardProgressPanel(self.steps)
        self.playlist_panel = ChannelWizardPlaylistPanel()

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.info_panel)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.progress_panel)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(left_widget)
        top_splitter.addWidget(right_widget)
        top_splitter.setSizes([520, 320])

        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.playlist_panel)
        main_splitter.setSizes([320, 230])

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(90)

        button_row = QHBoxLayout()

        self.btn_start = QPushButton("Einrichten")
        self.btn_close = QPushButton("Schließen")

        self.btn_start.clicked.connect(self.on_start_button_clicked)
        self.btn_close.clicked.connect(self.reject)

        button_row.addStretch()
        button_row.addWidget(self.btn_start)
        button_row.addWidget(self.btn_close)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(self.url_input)
        main_layout.addWidget(main_splitter)
        main_layout.addWidget(self.log)
        main_layout.addLayout(button_row)

    def on_start_button_clicked(self):
        if self.ready_to_save:
            self.save_channel_after_review()
        else:
            self.start_loading()

    def start_loading(self):
        self.url = self.url_input.toPlainText().strip()

        if not self.url:
            QMessageBox.warning(
                self,
                "Kanal-Assistent",
                "Bitte eine YouTube-Kanal-URL eingeben."
            )
            return

        self.btn_start.setEnabled(False)
        self.url_input.setEnabled(False)

        self.step_index = 0
        self.ready_to_save = False
        self.channel_info = {}
        self.detected_name = ""
        self.playlists = []
        self.created_channel = None
        self.created_index = None

        self.progress_panel.reset()
        self.playlist_panel.set_playlists([])
        self.log.clear()

        self.write_log("Einrichtung gestartet.")
        QTimer.singleShot(250, self.run_next_step)

    def run_next_step(self):
        if self.step_index > 6:
            self.enable_review_mode()
            return

        step = self.steps[self.step_index]
        self.progress_panel.set_running(self.step_index)

        try:
            if step == "Kanal-URL prüfen":
                self.check_url()
            elif step == "Kanal auf YouTube finden":
                self.find_channel()
            elif step == "Kanalname lesen":
                self.detect_channel_name()
            elif step == "Avatar vorbereiten":
                self.prepare_avatar()
            elif step == "Banner vorbereiten":
                self.prepare_banner()
            elif step == "Beschreibung lesen":
                self.prepare_description()
            elif step == "Playlists lesen":
                self.load_playlists()

            self.progress_panel.set_done(self.step_index)

        except Exception as error:
            self.progress_panel.set_warning(self.step_index)
            self.write_log(f"Warnung: {error}")

        self.step_index += 1
        self.progress_panel.set_progress(self.step_index)

        QTimer.singleShot(300, self.run_next_step)

    def enable_review_mode(self):
        self.ready_to_save = True
        self.btn_start.setText("Kanal speichern")
        self.btn_start.setEnabled(True)

        self.write_log(
            "Playlists können jetzt angepasst werden. "
            "Danach auf 'Kanal speichern' klicken."
        )

    def save_channel_after_review(self):
        self.btn_start.setEnabled(False)

        try:
            self.progress_panel.set_running(7)
            self.create_channel()
            self.progress_panel.set_done(7)
            self.progress_panel.set_progress(8)

            self.progress_panel.set_running(8)
            self.save_playlist_settings()
            self.progress_panel.set_done(8)
            self.progress_panel.set_progress(9)

            self.finish_success()

        except Exception as error:
            self.write_log(f"Fehler beim Speichern: {error}")
            self.btn_start.setEnabled(True)

    def check_url(self):
        if "youtube.com" not in self.url and "youtu.be" not in self.url:
            raise ValueError("Die URL sieht nicht wie eine YouTube-URL aus.")

        self.write_log("Kanal-URL geprüft.")

    def find_channel(self):
        self.write_log("YouTube-Daten werden gelesen...")

        self.channel_info = self.youtube_service.get_channel_info(self.url)

        if not self.channel_info:
            raise ValueError("Kanal konnte nicht gelesen werden.")

        self.write_log("Kanal wurde auf YouTube gefunden.")

    def detect_channel_name(self):
        name = self.channel_info.get("name", "").strip()

        if not name:
            name = self.guess_channel_name_from_url(self.url)
            self.write_log("Kein echter Kanalname gefunden, verwende Namen aus URL.")

        self.detected_name = name
        self.write_log(f"Kanalname: {name}")
        self.update_info_panel()

    def prepare_avatar(self):
        avatar = self.channel_info.get("avatar", "")

        if avatar:
            self.write_log("Avatar-URL gefunden.")
        else:
            self.write_log("Kein Avatar gefunden.")

        self.update_info_panel()

    def prepare_banner(self):
        banner = self.channel_info.get("banner", "")

        if banner:
            self.write_log("Banner-URL gefunden.")
        else:
            self.write_log("Kein Banner gefunden.")

        self.update_info_panel()

    def prepare_description(self):
        description = self.channel_info.get("description", "")

        if description:
            self.write_log("Beschreibung gelesen.")
        else:
            self.write_log("Keine Beschreibung gefunden.")

        self.update_info_panel()

    def load_playlists(self):
        self.write_log("Playlists werden gelesen...")

        temp_channel = Channel(
            name=self.detected_name or self.guess_channel_name_from_url(self.url),
            url=self.url
        )

        self.playlists = self.playlist_service.load_playlists(temp_channel)
        self.playlist_panel.set_playlists(self.playlists)

        if self.playlists:
            self.write_log(f"{len(self.playlists)} Playlists gefunden.")
        else:
            self.write_log("Keine Playlists gefunden.")

        self.update_info_panel()

    def create_channel(self):
        name = self.detected_name or self.guess_channel_name_from_url(self.url)
        channel_id = self.channel_info.get("id", "") or self.channel_info.get("channel_id", "")
        real_url = self.channel_info.get("url", "") or self.url

        channel = Channel(
            name=name,
            url=real_url,
            channel_id=channel_id,
            description=self.channel_info.get("description", "") or "",
        )

        avatar = self.channel_info.get("avatar", "")
        if avatar:
            saved = self.image_manager.save_channel_image(name, avatar, channel_id)
            channel.poster = saved or avatar
            if saved:
                self.write_log("Avatar/Kanalposter lokal gespeichert.")

        banner = self.channel_info.get("banner", "")
        if banner:
            saved = self.image_manager.save_banner_image(name, banner, channel_id)
            channel.fanart = saved or banner
            if saved:
                self.write_log("Banner/Fanart lokal gespeichert.")

        self.created_channel = channel
        self.created_index = self.controller.add_channel(channel)

        self.write_log("Kanal wurde angelegt.")

    def save_playlist_settings(self):
        if self.created_channel is None:
            raise ValueError("Kanal wurde noch nicht angelegt.")

        playlist_settings = self.playlist_panel.get_playlist_settings()

        if not playlist_settings:
            self.created_channel.playlist_settings = []
            self.controller.save()
            self.write_log("Keine Playlist-Einstellungen gespeichert.")
            return

        self.created_channel.playlist_settings = playlist_settings
        self.controller.save()

        active_count = sum(
            1 for setting in playlist_settings
            if setting.get("enabled", True)
        )

        self.write_log(
            f"Playlist-Einstellungen gespeichert: "
            f"{active_count}/{len(playlist_settings)} aktiv"
        )

    def update_info_panel(self):
        self.info_panel.set_channel_info(
            name=self.detected_name or self.guess_channel_name_from_url(self.url),
            url=self.url,
            description=self.channel_info.get("description", ""),
            avatar=self.channel_info.get("avatar", ""),
            banner=self.channel_info.get("banner", ""),
            playlist_count=len(self.playlists),
        )

    def finish_success(self):
        self.ready_to_save = False
        self.write_log("Einrichtung abgeschlossen.")
        self.btn_start.setText("Gespeichert")
        self.btn_close.setText("Fertig")

        try:
            self.btn_close.clicked.disconnect()
        except TypeError:
            pass

        self.btn_close.clicked.connect(self.accept)

    def write_log(self, text):
        self.log.append(text)

    def guess_channel_name_from_url(self, url):
        if not url:
            return "Neuer Kanal"

        parsed = urlparse(url.strip())
        path = unquote(parsed.path or "").strip("/")

        if not path:
            return "Neuer Kanal"

        parts = [part for part in path.split("/") if part]

        if not parts:
            return "Neuer Kanal"

        candidate = parts[-1]

        if candidate.lower() in ["videos", "playlists", "featured", "streams", "shorts"]:
            if len(parts) >= 2:
                candidate = parts[-2]

        if candidate.startswith("@"):
            candidate = candidate[1:]

        if candidate.lower() in ["channel", "c", "user"]:
            return "Neuer Kanal"

        candidate = re.sub(r"[-_]+", " ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()

        if not candidate:
            return "Neuer Kanal"

        return candidate.title()