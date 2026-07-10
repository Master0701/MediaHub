import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, unquote

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from src.mediahub.models.channel import Channel
from src.mediahub.gui.widgets.playlist_table import PlaylistTable
from src.mediahub.services.profile_service import ProfileService
from src.mediahub.services.image_manager import ImageAssetManager

try:
    from PIL import Image
except Exception:
    Image = None


class SetupWizard(QWizard):
    """Geführter Start-Assistent für komplette Kanal-/Download-Einrichtung.

    Der Assistent ist bewusst optional. Er schreibt erst beim Klick auf
    "Fertigstellen" in die Kanalverwaltung und legt danach optional Jobs oder
    Scheduler-Aufgaben an.
    """

    PAGE_URL = 0
    PAGE_FOLDERS = 1
    PAGE_NAMING = 2
    PAGE_PLAYLISTS = 3
    PAGE_AUTOMATION = 4
    PAGE_SUMMARY = 5

    def __init__(
        self,
        controller,
        youtube_service=None,
        playlist_service=None,
        repository=None,
        sync_manager=None,
        job_queue_manager=None,
        scheduler_manager=None,
        parent=None,
    ):
        super().__init__(parent)

        self.controller = controller
        self.youtube_service = youtube_service
        self.playlist_service = playlist_service
        self.repository = repository
        self.sync_manager = sync_manager
        self.job_queue_manager = job_queue_manager
        self.scheduler_manager = scheduler_manager

        self.channel_info = {}
        self.loaded_playlists = []
        self.created_channel = None
        self.created_index = None
        self.created_job_id = None
        self.created_task_id = None
        self.start_after_save = ""
        self.image_manager = ImageAssetManager(Path.cwd())

        self.setWindowTitle("MediaHub Start-Assistent")
        self.resize(940, 760)
        self.setMinimumSize(820, 620)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, False)
        self.setButtonText(QWizard.WizardButton.FinishButton, "Speichern")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter")
        self.setButtonText(QWizard.WizardButton.BackButton, "Zurück")
        self.setOption(QWizard.WizardOption.HaveCustomButton1, True)
        self.setButtonText(QWizard.WizardButton.CustomButton1, "Speichern und starten")
        self.customButtonClicked.connect(self._custom_button_clicked)

        self.url_page = UrlPage(self)
        self.folder_page = FolderPage(self)
        self.naming_page = NamingPage(self)
        self.playlist_page = PlaylistPage(self)
        self.automation_page = AutomationPage(self)
        self.summary_page = SummaryPage(self)

        self.setPage(self.PAGE_URL, self.url_page)
        self.setPage(self.PAGE_FOLDERS, self.folder_page)
        self.setPage(self.PAGE_NAMING, self.naming_page)
        self.setPage(self.PAGE_PLAYLISTS, self.playlist_page)
        self.setPage(self.PAGE_AUTOMATION, self.automation_page)
        self.setPage(self.PAGE_SUMMARY, self.summary_page)

    def guess_channel_name_from_url(self, url: str) -> str:
        parsed = urlparse((url or "").strip())
        path = unquote(parsed.path or "").strip("/")
        parts = [part for part in path.split("/") if part]
        if not parts:
            return "Neuer Kanal"
        candidate = parts[-1]
        if candidate.lower() in ["videos", "playlists", "featured", "streams", "shorts"] and len(parts) >= 2:
            candidate = parts[-2]
        if candidate.startswith("@"):
            candidate = candidate[1:]
        if candidate.lower() in ["channel", "c", "user"]:
            return "Neuer Kanal"
        candidate = re.sub(r"[-_]+", " ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        return candidate.title() if candidate else "Neuer Kanal"

    def load_youtube_data(self) -> None:
        url = self.url_page.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Start-Assistent", "Bitte zuerst eine YouTube-URL eingeben.")
            return
        if "youtube.com" not in url and "youtu.be" not in url:
            QMessageBox.warning(self, "Start-Assistent", "Die URL sieht nicht wie eine YouTube-URL aus.")
            return

        self.url_page.write_log("YouTube-Daten werden gelesen...")
        QApplication_process_events_safe()

        try:
            if self.youtube_service is not None:
                self.channel_info = self.youtube_service.get_channel_info(url) or {}
            else:
                self.channel_info = {}
        except Exception as error:
            self.channel_info = {}
            self.url_page.write_log(f"Kanalinfo konnte nicht gelesen werden: {error}")

        name = (self.channel_info.get("name") or "").strip() or self.guess_channel_name_from_url(url)
        if not self.url_page.name_edit.text().strip() or self.url_page.name_edit.text().strip() == "Neuer Kanal":
            self.url_page.name_edit.setText(name)
        self.folder_page.apply_default_folders(name)

        avatar_path = self.save_channel_image(name, self.channel_info.get("avatar", ""), "channel.jpg")
        banner_path = self.save_channel_image(name, self.channel_info.get("banner", ""), "banner.jpg")

        if avatar_path:
            self.naming_page.poster_edit.setText(avatar_path)
        elif self.channel_info.get("avatar"):
            self.naming_page.poster_edit.setText(self.channel_info.get("avatar", ""))

        if banner_path:
            self.naming_page.fanart_edit.setText(banner_path)
        elif self.channel_info.get("banner"):
            self.naming_page.fanart_edit.setText(self.channel_info.get("banner", ""))

        self.url_page.set_preview_images(avatar_path, banner_path)
        self.url_page.write_log(f"Kanal erkannt: {name}")

    def load_playlists(self) -> None:
        url = self.url_page.url_edit.text().strip()
        name = self.url_page.name_edit.text().strip() or self.guess_channel_name_from_url(url)
        if not url:
            QMessageBox.warning(self, "Start-Assistent", "Bitte zuerst eine YouTube-URL eingeben.")
            return
        if self.playlist_service is None:
            QMessageBox.warning(self, "Start-Assistent", "Playlist-Service ist nicht verfügbar.")
            return

        self.playlist_page.info_label.setText("Playlists werden geladen...")
        QApplication_process_events_safe()

        try:
            temp_channel = Channel(name=name, url=url)
            self.loaded_playlists = self.playlist_service.load_playlists(temp_channel) or []
            synced = self.playlist_service.sync_playlist_settings(temp_channel, self.loaded_playlists)
            for index, setting in enumerate(synced, start=1):
                thumbnail_url = setting.get("thumbnail_url", "")
                playlist_id = setting.get("playlist_id", "") or str(index)
                image_path = self.save_channel_image(
                    name,
                    thumbnail_url,
                    f"playlist_{self.safe_filename(playlist_id)}.jpg",
                )
                if image_path:
                    setting["image_path"] = image_path
            self.playlist_page.playlist_table.set_playlists(synced)
            if synced:
                self.playlist_page.info_label.setText(f"{len(synced)} Playlist(s) gefunden. Haken, Plex-Name und Staffel können angepasst werden.")
            else:
                self.playlist_page.info_label.setText("Keine Playlists gefunden. Der Kanal kann trotzdem gespeichert werden.")
        except Exception as error:
            self.loaded_playlists = []
            self.playlist_page.info_label.setText(f"Playlists konnten nicht geladen werden: {error}")

    def build_channel(self) -> Channel:
        name = self.url_page.name_edit.text().strip() or self.guess_channel_name_from_url(self.url_page.url_edit.text())
        channel = Channel(
            name=name,
            url=self.url_page.url_edit.text().strip(),
            profile=self.url_page.profile_combo.currentText(),
            audio_only=self.naming_page.audio_only_check.isChecked(),
            filename_template=self.naming_page.filename_template.currentText().strip() or "{title} S{season:02}E{episode:02}",
            work_folder=self.folder_page.work_folder_edit.text().strip(),
            target_folder=self.folder_page.target_folder_edit.text().strip(),
            poster=self.naming_page.poster_edit.text().strip(),
            fanart=self.naming_page.fanart_edit.text().strip(),
            container=self.naming_page.container_combo.currentText(),
            resolution=self.naming_page.resolution_combo.currentText(),
            audio_format=self.naming_page.audio_format_combo.currentText(),
            create_nfo=self.naming_page.create_nfo_check.isChecked(),
            create_poster=self.naming_page.create_poster_check.isChecked(),
            create_fanart=self.naming_page.create_fanart_check.isChecked(),
            clean_work_folder=self.naming_page.clean_work_folder_check.isChecked(),
            playlist_folder_mode=self.folder_page.playlist_folder_mode.currentText(),
            playlist_settings=self.playlist_page.playlist_table.get_playlist_settings(),
        )

        # Zusatzinfos aus der YouTube-Kanalerkennung speichern.
        # Wichtig für tvshow.nfo: Hier darf später NICHT die letzte
        # Videobeschreibung landen, sondern die echte Kanalbeschreibung.
        channel.channel_id = str(
            self.channel_info.get("id")
            or self.channel_info.get("channel_id")
            or self.channel_info.get("uploader_id")
            or ""
        ).strip()
        channel.description = str(
            self.channel_info.get("description")
            or self.channel_info.get("channel_description")
            or self.channel_info.get("about")
            or ""
        ).strip()
        channel.youtube_name = str(
            self.channel_info.get("name")
            or self.channel_info.get("title")
            or self.channel_info.get("channel")
            or name
            or ""
        ).strip()
        channel.channel_url = str(
            self.channel_info.get("webpage_url")
            or self.channel_info.get("channel_url")
            or self.url_page.url_edit.text().strip()
            or ""
        ).strip()

        return channel

    def safe_filename(self, value: str) -> str:
        text = re.sub(r'[<>:"/\\|?*]+', "_", str(value or "")).strip()
        text = re.sub(r"\s+", "_", text)
        return text or "image"

    def channel_assets_dir(self, channel_name: str) -> Path:
        folder = Path("assets") / "channels" / self.safe_filename(channel_name)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def save_channel_image(self, channel_name: str, url_or_path: str, filename: str) -> str:
        """Speichert Kanal-/Banner-/Playlistbilder lokal über ImageAssetManager."""
        source = str(url_or_path or "").strip()
        if not source:
            return ""

        if not hasattr(self, "image_manager") or self.image_manager is None:
            self.image_manager = ImageAssetManager(Path.cwd())

        channel_id = str(self.channel_info.get("id") or "").strip()
        filename = str(filename or "").strip()

        try:
            if filename == "channel.jpg":
                return self.image_manager.save_channel_image(channel_name, source, channel_id)
            if filename == "banner.jpg":
                return self.image_manager.save_banner_image(channel_name, source, channel_id)
            if filename.startswith("playlist_"):
                playlist_id = filename[len("playlist_"):].rsplit(".", 1)[0]
                return self.image_manager.save_playlist_image(channel_name, playlist_id, source, channel_id)

            destination = self.channel_assets_dir(channel_name) / filename
            return self.image_manager.save_image(source, destination, "poster")
        except Exception as error:
            try:
                self.url_page.write_log(f"Bild konnte nicht gespeichert werden: {error}")
            except Exception:
                pass
            return ""

    def convert_image_to_jpg(self, source: Path, destination: Path) -> bool:
        return self.image_manager.copy_or_convert_to_jpg(source, destination, "poster")

    def _custom_button_clicked(self, button) -> None:
        """Behandelt den Zusatzbutton „Speichern und starten".

        PySide liefert je nach Version entweder ein Enum oder einen Integer.
        Da es aktuell nur einen Custom-Button gibt, wird der Klick bewusst
        robust behandelt und startet immer den vollständigen Wizard-Ablauf:
        speichern → synchronisieren → neue Videos zur Auswahl öffnen.
        """
        self.automation_page.create_job_check.setChecked(True)
        self.automation_page.start_sync_now_check.setChecked(True)
        self.automation_page.start_download_after_sync_check.setChecked(True)
        self.start_after_save = "sync_download"
        self.accept()

    def accept(self) -> None:
        try:
            channel = self.build_channel()
            self.created_channel = channel
            self.created_index = self.controller.add_channel(channel)

            if self.repository is not None:
                try:
                    self.repository.sync_channels(self.controller.get_channels())
                except Exception:
                    pass

            if self.automation_page.create_job_check.isChecked() and self.job_queue_manager is not None:
                self.created_job_id = self.job_queue_manager.add_sync_job_for_channel(channel)

            if self.automation_page.create_scheduler_check.isChecked() and self.scheduler_manager is not None:
                self.created_task_id = self.scheduler_manager.add_sync_task_for_channel(
                    channel,
                    interval_hours=self.automation_page.interval_spin.value(),
                )

            if self.automation_page.start_download_after_sync_check.isChecked():
                self.start_after_save = "sync_download"
            elif self.automation_page.start_sync_now_check.isChecked():
                self.start_after_save = "sync"

            super().accept()
        except Exception as error:
            QMessageBox.critical(self, "Start-Assistent", f"Speichern fehlgeschlagen:\n{error}")


class UrlPage(QWizardPage):
    def __init__(self, wizard: SetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.setTitle("1. Quelle / Kanal")
        self.setSubTitle("Füge die YouTube-URL ein. MediaHub kann Name, Avatar, Banner und Playlists automatisch vorbereiten.")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://youtube.com/@Kanalname")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("wird automatisch erkannt oder manuell eingetragen")
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(ProfileService.names())

        self.url_edit.setToolTip("Kanal-, Playlist- oder Video-URL. Beispiel: https://youtube.com/@RichterAlexanderHold")
        self.name_edit.setToolTip("Anzeigename in MediaHub. Beispiel: Richter Alexander Hold")
        self.profile_combo.setToolTip("Voreinstellung für Namensschema und Medienart.")

        form.addRow("YouTube-URL", self.url_edit)
        form.addRow("Kanalname", self.name_edit)
        form.addRow("Profil", self.profile_combo)
        layout.addLayout(form)

        help_text = QLabel(
            "Beispiel: URL einfügen → „Kanal-Daten lesen“ klicken → MediaHub schlägt Name und Ordner automatisch vor."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #b8c0cc;")
        layout.addWidget(help_text)

        image_row = QHBoxLayout()
        self.avatar_label = QLabel("Kein Kanalbild")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedSize(120, 120)
        self.avatar_label.setStyleSheet("border: 1px solid #3a4654; background: #202833; color: #b8c0cc;")
        self.banner_label = QLabel("Kein Banner")
        self.banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner_label.setFixedHeight(120)
        self.banner_label.setMinimumWidth(360)
        self.banner_label.setStyleSheet("border: 1px solid #3a4654; background: #202833; color: #b8c0cc;")
        image_row.addWidget(self.avatar_label)
        image_row.addWidget(self.banner_label, 1)
        layout.addLayout(image_row)

        row = QHBoxLayout()
        self.btn_detect = QPushButton("Kanal-Daten lesen")
        self.btn_detect.clicked.connect(self.wizard_ref.load_youtube_data)
        row.addWidget(self.btn_detect)
        row.addStretch()
        layout.addLayout(row)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(110)
        layout.addWidget(self.log)

        self.url_edit.textChanged.connect(self._maybe_fill_name)
        self.name_edit.textChanged.connect(self._name_changed)
        self.registerField("channel_url*", self.url_edit)
        self.registerField("channel_name*", self.name_edit)

    def _maybe_fill_name(self):
        current_name = self.name_edit.text().strip()
        if current_name and current_name != "Neuer Kanal":
            return
        guessed = self.wizard_ref.guess_channel_name_from_url(self.url_edit.text())
        if guessed and guessed != "Neuer Kanal":
            self.name_edit.setText(guessed)
            self.wizard_ref.folder_page.apply_default_folders(guessed)

    def _name_changed(self):
        name = self.name_edit.text().strip()
        if name:
            self.wizard_ref.folder_page.apply_default_folders(name)
            try:
                self.wizard_ref.naming_page.update_preview()
            except Exception:
                pass

    def set_preview_images(self, avatar_path: str = "", banner_path: str = "") -> None:
        if avatar_path and Path(avatar_path).exists():
            pixmap = QPixmap(avatar_path)
            if not pixmap.isNull():
                self.avatar_label.setPixmap(
                    pixmap.scaled(
                        self.avatar_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.avatar_label.setText("")
        elif hasattr(self, "avatar_label"):
            self.avatar_label.setText("Kein Kanalbild")
            self.avatar_label.setPixmap(QPixmap())

        if banner_path and Path(banner_path).exists():
            pixmap = QPixmap(banner_path)
            if not pixmap.isNull():
                self.banner_label.setPixmap(
                    pixmap.scaled(
                        self.banner_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.banner_label.setText("")
        elif hasattr(self, "banner_label"):
            self.banner_label.setText("Kein Banner")
            self.banner_label.setPixmap(QPixmap())

    def write_log(self, text: str) -> None:
        self.log.append(text)

    def validatePage(self) -> bool:
        url = self.url_edit.text().strip()
        if "youtube.com" not in url and "youtu.be" not in url:
            QMessageBox.warning(self, "Start-Assistent", "Bitte eine gültige YouTube-URL eingeben.")
            return False
        if not self.name_edit.text().strip():
            self.name_edit.setText(self.wizard_ref.guess_channel_name_from_url(url))
        self.wizard_ref.folder_page.apply_default_folders(self.name_edit.text().strip())
        return True


class FolderPage(QWizardPage):
    def __init__(self, wizard: SetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.setTitle("2. Ordner")
        self.setSubTitle("Lege Arbeitsordner und optional Plex-/Zielordner fest. Ohne Zielordner bleiben Dateien im Arbeitsordner.")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.work_folder_edit = QLineEdit()
        self.target_folder_edit = QLineEdit()
        self._last_auto_work = ""
        self._last_auto_target = ""
        self.playlist_folder_mode = QComboBox()
        self.playlist_folder_mode.addItems(["Nur Staffeln", "Playlist-Ordner", "Keine Unterordner"])

        self.work_folder_edit.setPlaceholderText(r"downloads\work\Kanalname")
        self.target_folder_edit.setPlaceholderText(r"downloads\Fertig\Kanalname")
        self.work_folder_edit.setToolTip("Temporärer Arbeitsordner. Hier lädt MediaHub zuerst herunter und erzeugt Sidecar-Dateien.")
        self.target_folder_edit.setToolTip(r"Fertiger Zielordner. Beispiel: downloads\Fertig\Richter Alexander Hold")
        self.playlist_folder_mode.setToolTip("Legt fest, ob aktive Playlists als eigene Unterordner oder nur als Staffeln sortiert werden.")

        form.addRow("Arbeitsordner", self._file_row(self.work_folder_edit, True))
        form.addRow("Zielordner / Plex", self._file_row(self.target_folder_edit, True))
        form.addRow("Playlist-Ordner", self.playlist_folder_mode)
        layout.addLayout(form)

        help_text = QLabel(
            "Kurz erklärt:\n"
            "• Arbeitsordner: Zwischenablage für laufende Downloads und temporäre Dateien.\n"
            "• Zielordner: fertiger Ausgabeordner/Plex-Ordner.\n"
            "• Playlist-Ordner: legt fest, ob mehrere Playlists eigene Unterordner bekommen."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #b8c0cc;")
        layout.addWidget(help_text)

        preview_box = QGroupBox("Live-Vorschau Ordnerstruktur")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_label = QLabel("Beispiel wird nach dem Kanalnamen automatisch gesetzt.")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #8fb3ff;")
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_box)

        self.work_folder_edit.textChanged.connect(self.update_preview)
        self.target_folder_edit.textChanged.connect(self.update_preview)
        self.playlist_folder_mode.currentTextChanged.connect(self.update_preview)
        layout.addStretch()

    def _file_row(self, line_edit: QLineEdit, folder: bool) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self._browse(line_edit, folder))
        row.addWidget(line_edit)
        row.addWidget(button)
        return widget

    def _browse(self, line_edit: QLineEdit, folder: bool) -> None:
        path = QFileDialog.getExistingDirectory(self, "Ordner auswählen") if folder else QFileDialog.getOpenFileName(self, "Datei auswählen")[0]
        if path:
            line_edit.setText(path)

    def apply_default_folders(self, channel_name: str) -> None:
        safe_name = re.sub(r'[<>:"/\\|?*]+', "_", (channel_name or "Neuer Kanal")).strip() or "Neuer Kanal"
        safe_name = re.sub(r"\s+", " ", safe_name)

        work_default = str(Path("downloads") / "work" / safe_name)
        target_default = str(Path("downloads") / "Fertig" / safe_name)

        current_work = self.work_folder_edit.text().strip()
        current_target = self.target_folder_edit.text().strip()

        if not current_work or current_work == self._last_auto_work:
            self.work_folder_edit.setText(work_default)
            self._last_auto_work = work_default
        if not current_target or current_target == self._last_auto_target:
            self.target_folder_edit.setText(target_default)
            self._last_auto_target = target_default

        self.update_preview()

    def get_example_output_folder(self) -> str:
        target = self.target_folder_edit.text().strip() or str(Path("downloads") / "Fertig" / "Beispiel Kanal")
        mode = self.playlist_folder_mode.currentText()
        playlist_name = "Ganze Folgen"
        season_folder = "Season 01"

        if mode == "Playlist-Ordner":
            return str(Path(target) / playlist_name / season_folder)
        if mode == "Nur Staffeln":
            return str(Path(target) / season_folder)
        return target

    def update_preview(self) -> None:
        work = self.work_folder_edit.text().strip() or str(Path("downloads") / "work" / "Beispiel Kanal")
        target = self.target_folder_edit.text().strip() or str(Path("downloads") / "Fertig" / "Beispiel Kanal")
        final_folder = self.get_example_output_folder()
        mode = self.playlist_folder_mode.currentText()

        mode_text = {
            "Playlist-Ordner": "Zielordner → Playlist → Staffel → Datei",
            "Nur Staffeln": "Zielordner → Staffel → Datei",
            "Keine Unterordner": "Zielordner → Datei",
        }.get(mode, mode)

        self.preview_label.setText(
            "Beispiel mit Testvideo:\n"
            f"Arbeitsordner: {work}\n"
            f"Zielordner: {target}\n"
            f"Sortierung: {mode_text}\n"
            f"Fertiger Beispielordner: {final_folder}"
        )

        try:
            self.wizard_ref.naming_page.update_preview()
        except Exception:
            pass


class NamingPage(QWizardPage):
    def __init__(self, wizard: SetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.setTitle("3. Download / Benennung")
        self.setSubTitle("Wähle Dateiname und Qualität. Details sind einklappbar, damit die Seite übersichtlich bleibt.")

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self.filename_template = QComboBox()
        self.filename_template.setEditable(True)
        self.filename_template.addItems([
            "{title} S{season:02}E{episode:02}",
            "S{season:02}E{episode:02} {title}",
            "{title} (S{season:02}E{episode:02})",
            "{title} - S{season:02}E{episode:02}",
            "{series} - {title} S{season:02}E{episode:02}",
            "{series} - S{season:02}E{episode:02} - {title}",
        ])

        self.container_combo = QComboBox()
        self.container_combo.addItems(["MKV", "MP4", "WebM"])
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Beste", "4K", "1440p", "1080p", "720p", "480p"])
        self.resolution_combo.setCurrentText("1080p")
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["M4A", "MP3", "AAC", "FLAC", "OGG", "WAV"])

        self.poster_edit = QLineEdit()
        self.fanart_edit = QLineEdit()

        self.filename_template.setToolTip("Platzhalter: {title}, {series}, {season}, {episode}, {year}. Beispiel: Richter Alexander Hold - S01E01 - Titel")
        self.container_combo.setToolTip("Video-Container für fertige Dateien. MKV ist meist am stabilsten.")
        self.resolution_combo.setToolTip("Maximale Qualität. 1080p ist ein guter Standard.")
        self.audio_format_combo.setToolTip("Nur relevant, wenn „Nur Audio herunterladen“ aktiviert ist.")
        self.poster_edit.setToolTip("Optional: Avatar/Poster-URL oder Datei. Wird oft automatisch erkannt.")
        self.fanart_edit.setToolTip("Optional: Banner/Fanart-URL oder Datei. Wird oft automatisch erkannt.")

        form_box = QGroupBox("Dateiname und Qualität")
        form = QFormLayout(form_box)
        form.setVerticalSpacing(6)
        form.addRow("Dateinamenschema", self.filename_template)

        quality_row = QWidget()
        quality_layout = QGridLayout(quality_row)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        quality_layout.setHorizontalSpacing(8)
        quality_layout.addWidget(QLabel("Container"), 0, 0)
        quality_layout.addWidget(self.container_combo, 0, 1)
        quality_layout.addWidget(QLabel("Auflösung"), 0, 2)
        quality_layout.addWidget(self.resolution_combo, 0, 3)
        quality_layout.addWidget(QLabel("Audio"), 0, 4)
        quality_layout.addWidget(self.audio_format_combo, 0, 5)
        quality_layout.setColumnStretch(1, 1)
        quality_layout.setColumnStretch(3, 1)
        quality_layout.setColumnStretch(5, 1)
        form.addRow("Qualität", quality_row)
        layout.addWidget(form_box)

        advanced_box = QGroupBox("Poster/Fanart anzeigen")
        advanced_box.setCheckable(True)
        advanced_box.setChecked(False)
        advanced_layout = QFormLayout(advanced_box)

        poster_row = QHBoxLayout()
        poster_row.addWidget(self.poster_edit, 1)
        self.btn_choose_poster = QPushButton("Bild wählen")
        self.btn_choose_poster.clicked.connect(self.choose_poster_image)
        poster_row.addWidget(self.btn_choose_poster)

        fanart_row = QHBoxLayout()
        fanart_row.addWidget(self.fanart_edit, 1)
        self.btn_choose_fanart = QPushButton("Bild wählen")
        self.btn_choose_fanart.clicked.connect(self.choose_fanart_image)
        fanart_row.addWidget(self.btn_choose_fanart)

        advanced_layout.addRow("Poster/Avatar", poster_row)
        advanced_layout.addRow("Fanart/Banner", fanart_row)
        self.poster_edit.setVisible(False)
        self.fanart_edit.setVisible(False)
        self.btn_choose_poster.setVisible(False)
        self.btn_choose_fanart.setVisible(False)
        for label in advanced_box.findChildren(QLabel):
            label.setVisible(False)
        def _toggle_advanced(checked):
            self.poster_edit.setVisible(checked)
            self.fanart_edit.setVisible(checked)
            self.btn_choose_poster.setVisible(checked)
            self.btn_choose_fanart.setVisible(checked)
            for label in advanced_box.findChildren(QLabel):
                label.setVisible(checked)
        advanced_box.toggled.connect(_toggle_advanced)
        layout.addWidget(advanced_box)

        preview_box = QGroupBox("Live-Vorschau")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #8fb3ff;")
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_box)

        options = QGroupBox("Optionen anzeigen")
        options.setCheckable(True)
        options.setChecked(False)
        opt_layout = QGridLayout(options)
        self.audio_only_check = QCheckBox("Nur Audio herunterladen")
        self.create_nfo_check = QCheckBox("NFO erzeugen")
        self.create_poster_check = QCheckBox("Poster erzeugen")
        self.create_fanart_check = QCheckBox("Fanart erzeugen")
        self.clean_work_folder_check = QCheckBox("Arbeitsordner nach Import leeren")
        self.create_nfo_check.setChecked(True)
        self.create_poster_check.setChecked(True)
        self.create_fanart_check.setChecked(True)
        self.clean_work_folder_check.setChecked(True)
        option_widgets = (
            self.audio_only_check,
            self.create_nfo_check,
            self.create_poster_check,
            self.create_fanart_check,
            self.clean_work_folder_check,
        )
        for index, widget in enumerate(option_widgets):
            opt_layout.addWidget(widget, index // 2, index % 2)
        for child in option_widgets:
            child.setVisible(False)
        def _toggle_options(checked):
            for child in option_widgets:
                child.setVisible(checked)
        options.toggled.connect(_toggle_options)
        layout.addWidget(options)

        self.placeholder_box = QGroupBox("Platzhalter anzeigen")
        self.placeholder_box.setCheckable(True)
        self.placeholder_box.setChecked(False)
        placeholder_layout = QVBoxLayout(self.placeholder_box)
        self.placeholder_help = QLabel(
            "{series}  = Kanal/Serienname, z. B. Richter Alexander Hold\n"
            "{title}   = Videotitel\n"
            "{season}  = Staffelnummer, z. B. 01\n"
            "{episode} = Folgenummer, z. B. 01\n"
            "{year}    = Jahr, wenn verfügbar, z. B. 2026\n\n"
            "Beispiel:\n"
            "{series} - S{season:02}E{episode:02} - {title}"
        )
        self.placeholder_help.setWordWrap(True)
        self.placeholder_help.setStyleSheet("color: #b8c0cc;")
        placeholder_layout.addWidget(self.placeholder_help)
        self.placeholder_help.setVisible(False)
        self.placeholder_box.toggled.connect(self.placeholder_help.setVisible)
        layout.addWidget(self.placeholder_box)

        self.filename_template.currentTextChanged.connect(self.update_preview)
        self.container_combo.currentTextChanged.connect(self.update_preview)
        self.resolution_combo.currentTextChanged.connect(self.update_preview)
        self.audio_format_combo.currentTextChanged.connect(self.update_preview)
        self.audio_only_check.toggled.connect(self.update_preview)
        self.create_nfo_check.toggled.connect(self.update_preview)
        self.create_poster_check.toggled.connect(self.update_preview)
        self.create_fanart_check.toggled.connect(self.update_preview)
        self.update_preview()
        layout.addStretch()

    def choose_poster_image(self) -> None:
        path = QFileDialog.getOpenFileName(
            self,
            "Poster/Kanalbild auswählen",
            "",
            "Bilder (*.jpg *.jpeg *.png *.webp);;Alle Dateien (*.*)",
        )[0]
        if path:
            self.poster_edit.setText(path)
            self.update_preview()

    def choose_fanart_image(self) -> None:
        path = QFileDialog.getOpenFileName(
            self,
            "Fanart/Banner auswählen",
            "",
            "Bilder (*.jpg *.jpeg *.png *.webp);;Alle Dateien (*.*)",
        )[0]
        if path:
            self.fanart_edit.setText(path)
            self.update_preview()

    def _format_example_filename(self) -> str:
        template = self.filename_template.currentText().strip() or "{title} S{season:02}E{episode:02}"
        data = {
            "series": self.wizard_ref.url_page.name_edit.text().strip() or "Richter Alexander Hold",
            "title": "Brutaler Doppelmord",
            "season": 1,
            "episode": 1,
            "year": 2026,
        }
        try:
            name = template.format(**data)
        except Exception:
            name = template
        suffix = (self.audio_format_combo.currentText() if self.audio_only_check.isChecked() else self.container_combo.currentText()).lower()
        return f"{name}.{suffix}"

    def update_preview(self) -> None:
        filename = self._format_example_filename()
        try:
            folder = self.wizard_ref.folder_page.get_example_output_folder()
        except Exception:
            folder = str(Path("downloads") / "Fertig" / "Richter Alexander Hold" / "Season 01")

        sidecars = []
        if self.create_nfo_check.isChecked():
            sidecars.append(".nfo")
        if self.create_poster_check.isChecked():
            sidecars.append("-poster.jpg")
        if self.create_fanart_check.isChecked():
            sidecars.append("-fanart.jpg")
        sidecar_text = ", ".join(sidecars) if sidecars else "keine"

        quality = "Audio" if self.audio_only_check.isChecked() else self.resolution_combo.currentText()
        self.preview_label.setText(
            "So wird ein Beispiel-Download abgelegt:\n"
            f"Ordner: {folder}\n"
            f"Datei: {filename}\n"
            f"Qualität: {quality}\n"
            f"Zusatzdateien: {sidecar_text}"
        )


class PlaylistPage(QWizardPage):
    def __init__(self, wizard: SetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.setTitle("4. Playlists")
        self.setSubTitle("Playlists können automatisch gelesen und direkt aktiviert/deaktiviert werden.")

        layout = QVBoxLayout(self)
        self.info_label = QLabel("Noch keine Playlists geladen.")
        self.playlist_table = PlaylistTable()
        self.playlist_table.setMinimumHeight(260)
        self.btn_load = QPushButton("Playlists laden")
        self.btn_load.clicked.connect(self.wizard_ref.load_playlists)
        help_text = QLabel(
            "Haken aktiv = Playlist wird bei Vorschau, Sync und Scheduler berücksichtigt. \
Plex-Name/Staffel helfen später bei sauberer Sortierung."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #b8c0cc;")
        layout.addWidget(self.info_label)
        layout.addWidget(help_text)
        layout.addWidget(self.playlist_table)
        layout.addWidget(self.btn_load)


class AutomationPage(QWizardPage):
    def __init__(self, wizard: SetupWizard):
        super().__init__()
        self.setTitle("5. Jobs / Scheduler")
        self.setSubTitle("Lege fest, ob MediaHub nach dem Speichern direkt Jobs oder automatische Aufgaben vorbereiten soll.")

        layout = QVBoxLayout(self)
        self.create_job_check = QCheckBox("Direkt einen Sync-Job anlegen")
        self.create_scheduler_check = QCheckBox("Scheduler-Aufgabe anlegen")
        self.start_sync_now_check = QCheckBox("Nach dem Speichern sofort synchronisieren")
        self.start_download_after_sync_check = QCheckBox("Danach neue Videos zur Download-Auswahl öffnen")
        self.create_job_check.setChecked(True)

        interval_row = QHBoxLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 24 * 30)
        self.interval_spin.setValue(24)
        interval_row.addWidget(QLabel("Scheduler-Intervall:"))
        interval_row.addWidget(self.interval_spin)
        interval_row.addWidget(QLabel("Stunde(n)"))
        interval_row.addStretch()

        self.create_job_check.setToolTip("Legt einen einmaligen Sync-Job in der Job-Queue an. Spalte Geplant zeigt dann Manuell/Sofort.")
        self.create_scheduler_check.setToolTip("Legt eine wiederkehrende Aufgabe an, die automatisch Jobs erzeugt.")
        self.start_sync_now_check.setToolTip("Synchronisiert den Kanal nach dem Speichern sofort.")
        self.start_download_after_sync_check.setToolTip("Nach dem Sync werden neu gefundene Videos in der Videoauswahl angezeigt. Erst wenn du dort bestätigst, startet der Download.")

        layout.addWidget(self.create_job_check)
        layout.addWidget(self.create_scheduler_check)
        layout.addLayout(interval_row)
        layout.addWidget(self.start_sync_now_check)
        layout.addWidget(self.start_download_after_sync_check)
        help_text = QLabel(
            "Kurz erklärt:\n"
            "• Sync liest Playlists und schreibt neue Videos in die Bibliothek.\n"
            "• Download startet erst nach Bestätigung in der Videoauswahl. Dann werden Arbeits-/Zielordner erstellt.\n"
            "• Scheduler = wiederkehrende Aufgabe, z. B. alle 12 Stunden prüfen.\n"
            "• Geplant in der Job-Liste zeigt den geplanten Start oder Manuell/Sofort."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #b8c0cc;")
        layout.addWidget(help_text)
        layout.addStretch()


class SummaryPage(QWizardPage):
    def __init__(self, wizard: SetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.setTitle("6. Übersicht")
        self.setSubTitle("Prüfe die Angaben. Mit Speichern wird alles ins Programm übernommen.")
        layout = QVBoxLayout(self)
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        layout.addWidget(self.summary)

    def initializePage(self) -> None:
        wizard = self.wizard_ref
        playlist_settings = wizard.playlist_page.playlist_table.get_playlist_settings()
        active_playlists = sum(1 for setting in playlist_settings if setting.get("enabled", True))
        text = (
            f"Kanal: {wizard.url_page.name_edit.text().strip()}\n"
            f"URL: {wizard.url_page.url_edit.text().strip()}\n"
            f"Profil: {wizard.url_page.profile_combo.currentText()}\n\n"
            f"Arbeitsordner: {wizard.folder_page.work_folder_edit.text().strip() or '-'}\n"
            f"Zielordner: {wizard.folder_page.target_folder_edit.text().strip() or '-'}\n\n"
            f"Dateiname: {wizard.naming_page.filename_template.currentText()}\n"
            f"Container: {wizard.naming_page.container_combo.currentText()}\n"
            f"Auflösung: {wizard.naming_page.resolution_combo.currentText()}\n"
            f"Audio: {wizard.naming_page.audio_format_combo.currentText()}\n"
            f"NFO: {'ja' if wizard.naming_page.create_nfo_check.isChecked() else 'nein'}\n\n"
            f"Playlists: {active_playlists}/{len(playlist_settings)} aktiv\n\n"
            f"Sync-Job anlegen: {'ja' if wizard.automation_page.create_job_check.isChecked() else 'nein'}\n"
            f"Scheduler: {'ja, alle ' + str(wizard.automation_page.interval_spin.value()) + ' Stunde(n)' if wizard.automation_page.create_scheduler_check.isChecked() else 'nein'}\n"
            f"Sofort synchronisieren: {'ja' if wizard.automation_page.start_sync_now_check.isChecked() else 'nein'}\n"
            f"Danach Download-Auswahl öffnen: {'ja' if wizard.automation_page.start_download_after_sync_check.isChecked() else 'nein'}\n"
        )
        self.summary.setPlainText(text)


def QApplication_process_events_safe():
    try:
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
    except Exception:
        pass
