from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QMessageBox,
    QScrollArea,
)

from src.mediahub.services.settings_service import SettingsService
from src.mediahub.services.profile_service import ProfileService


class GlobalSettingsPanel(QWidget):
    """Programmweite Einstellungen.

    Wichtig: Kanalspezifische Optionen bleiben im rechten Bereich der Kanalseite.
    Diese Seite ist fuer globale Pfade, Defaults, Backup und Tool-Status gedacht.
    """

    PLAYLIST_FOLDER_MODES = [
        "Nur Staffeln",
        "Playlist → Staffel",
        "Playlist ohne Staffel",
        "Staffel = Playlist",
    ]

    def __init__(self, base_dir: Path, tool_service=None, parent=None):
        super().__init__(parent)
        self.base_dir = Path(base_dir)
        self.tool_service = tool_service
        self.settings_service = SettingsService(self.base_dir)
        self._loading = False

        outer = QVBoxLayout(self)

        title = QLabel("⚙ Globale Einstellungen")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        outer.addWidget(title)

        hint = QLabel(
            "Hier stellst du MediaHub allgemein ein. "
            "Kanalspezifische Optionen findest du weiterhin auf der Seite „Kanäle“."
        )
        hint.setWordWrap(True)
        outer.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, 1)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(14)
        scroll.setWidget(content)

        self._build_paths_group()
        self._build_download_defaults_group()
        self._build_plex_defaults_group()
        self._build_backup_group()
        self._build_tools_group()
        self._build_ui_group()
        self.content_layout.addStretch(1)

        buttons = QHBoxLayout()
        self.btn_save = QPushButton("💾 Einstellungen speichern")
        self.btn_reload = QPushButton("↻ Neu laden")
        self.btn_reset = QPushButton("Standardwerte")
        self.btn_save.setMinimumHeight(34)
        self.btn_reload.setMinimumHeight(34)
        self.btn_reset.setMinimumHeight(34)

        self.btn_save.clicked.connect(self.save_settings)
        self.btn_reload.clicked.connect(self.load_settings)
        self.btn_reset.clicked.connect(self.reset_settings)

        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_reload)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_reset)
        outer.addLayout(buttons)

        self.load_settings()

    def _build_paths_group(self):
        group = QGroupBox("Ordnerpfade")
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.path_downloads = self._path_row(layout, "Downloads:")
        self.path_finished = self._path_row(layout, "Fertig:")
        self.path_work = self._path_row(layout, "Arbeitsordner:")
        self.path_backups = self._path_row(layout, "Backups:")
        self.path_logs = self._path_row(layout, "Logs:")
        self.path_tools = self._path_row(layout, "Tools:")

        self.content_layout.addWidget(group)

    def _path_row(self, form: QFormLayout, label: str) -> QLineEdit:
        edit = QLineEdit()
        browse = QPushButton("Auswählen")
        open_btn = QPushButton("Öffnen")
        browse.setMinimumHeight(30)
        open_btn.setMinimumHeight(30)
        browse.clicked.connect(lambda: self._choose_folder(edit))
        open_btn.clicked.connect(lambda: self._open_folder(edit.text()))

        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(browse)
        row.addWidget(open_btn)
        form.addRow(label, row)
        return edit

    def _build_download_defaults_group(self):
        group = QGroupBox("Download-Standardwerte für neue Kanäle")
        layout = QFormLayout(group)

        self.default_profile = QComboBox()
        self.default_profile.addItems(ProfileService.names())
        self.default_container = QComboBox()
        self.default_container.addItems(["MKV", "MP4", "WebM"])
        self.default_resolution = QComboBox()
        self.default_resolution.addItems(["Beste", "4K", "1440p", "1080p", "720p", "480p"])
        self.default_audio = QComboBox()
        self.default_audio.addItems(["M4A", "MP3", "AAC", "FLAC", "OGG", "WAV"])
        self.default_audio_only = QCheckBox("Neue Kanäle standardmäßig als Audio laden")
        self.default_clean_work = QCheckBox("Arbeitsordner nach Import standardmäßig leeren")

        layout.addRow("Profil:", self.default_profile)
        layout.addRow("Container:", self.default_container)
        layout.addRow("Auflösung:", self.default_resolution)
        layout.addRow("Audioformat:", self.default_audio)
        layout.addRow("", self.default_audio_only)
        layout.addRow("", self.default_clean_work)

        self.content_layout.addWidget(group)

    def _build_plex_defaults_group(self):
        group = QGroupBox("Plex-/Archiv-Standardwerte")
        layout = QFormLayout(group)

        self.create_nfo = QCheckBox("NFO erzeugen")
        self.create_poster = QCheckBox("Poster erzeugen")
        self.create_fanart = QCheckBox("Fanart erzeugen")
        self.playlist_folder_mode = QComboBox()
        self.playlist_folder_mode.addItems(self.PLAYLIST_FOLDER_MODES)

        layout.addRow("", self.create_nfo)
        layout.addRow("", self.create_poster)
        layout.addRow("", self.create_fanart)
        layout.addRow("Playlist-Ablage:", self.playlist_folder_mode)

        self.content_layout.addWidget(group)

    def _build_backup_group(self):
        group = QGroupBox("Automatische Backups")
        layout = QFormLayout(group)

        self.backup_enabled = QCheckBox("Automatische Backups aktivieren")
        self.backup_interval = QComboBox()
        self.backup_interval.addItems(["Täglich", "Wöchentlich", "Monatlich"])
        self.backup_keep_count = QSpinBox()
        self.backup_keep_count.setRange(1, 999)
        self.backup_keep_count.setSuffix(" Backups behalten")

        self.backup_include_config = QCheckBox("Konfiguration sichern")
        self.backup_include_database = QCheckBox("Datenbank sichern")
        self.backup_include_logs = QCheckBox("Logs mitsichern")
        self.backup_include_downloads = QCheckBox("Downloads mitsichern")

        layout.addRow("", self.backup_enabled)
        layout.addRow("Intervall:", self.backup_interval)
        layout.addRow("Aufbewahrung:", self.backup_keep_count)
        layout.addRow("", self.backup_include_config)
        layout.addRow("", self.backup_include_database)
        layout.addRow("", self.backup_include_logs)
        layout.addRow("", self.backup_include_downloads)

        self.content_layout.addWidget(group)

    def _build_tools_group(self):
        group = QGroupBox("Tool-Status")
        layout = QVBoxLayout(group)

        self.tool_status = QLabel("Noch nicht geprüft.")
        self.tool_status.setWordWrap(True)
        layout.addWidget(self.tool_status)

        row = QHBoxLayout()
        self.btn_check_tools = QPushButton("Tools prüfen")
        self.btn_open_tools = QPushButton("Tools-Ordner öffnen")
        self.btn_check_tools.setMinimumHeight(32)
        self.btn_open_tools.setMinimumHeight(32)
        self.btn_check_tools.clicked.connect(self.refresh_tools)
        self.btn_open_tools.clicked.connect(lambda: self._open_folder(self.path_tools.text()))
        row.addWidget(self.btn_check_tools)
        row.addWidget(self.btn_open_tools)
        row.addStretch(1)
        layout.addLayout(row)

        self.content_layout.addWidget(group)

    def _build_ui_group(self):
        group = QGroupBox("Oberfläche")
        layout = QFormLayout(group)

        self.start_page = QComboBox()
        self.start_page.addItems([
            "Dashboard",
            "Kanäle",
            "Bibliothek",
            "Downloads",
            "Jobs",
            "Scheduler",
            "Statistik",
            "Recovery",
        ])
        self.confirm_restore = QCheckBox("Vor Wiederherstellung Sicherheitsabfrage anzeigen")

        layout.addRow("Startseite:", self.start_page)
        layout.addRow("", self.confirm_restore)
        self.content_layout.addWidget(group)

    def load_settings(self):
        self._loading = True
        data = self.settings_service.load()

        paths = data.get("paths", {})
        self.path_downloads.setText(paths.get("downloads_dir", ""))
        self.path_finished.setText(paths.get("finished_dir", ""))
        self.path_work.setText(paths.get("work_dir", ""))
        self.path_backups.setText(paths.get("backup_dir", ""))
        self.path_logs.setText(paths.get("logs_dir", ""))
        self.path_tools.setText(paths.get("tools_dir", ""))

        download = data.get("download", {})
        self._set_combo(self.default_profile, download.get("default_profile", "Plex"))
        self._set_combo(self.default_container, download.get("default_container", "MKV"))
        self._set_combo(self.default_resolution, download.get("default_resolution", "1080p"))
        self._set_combo(self.default_audio, download.get("default_audio_format", "M4A"))
        self.default_audio_only.setChecked(bool(download.get("audio_only", False)))
        self.default_clean_work.setChecked(bool(download.get("clean_work_folder", True)))

        plex = data.get("plex", {})
        self.create_nfo.setChecked(bool(plex.get("create_nfo", True)))
        self.create_poster.setChecked(bool(plex.get("create_poster", True)))
        self.create_fanart.setChecked(bool(plex.get("create_fanart", True)))
        self._set_combo(self.playlist_folder_mode, plex.get("playlist_folder_mode", "Nur Staffeln"))

        backup = data.get("backup", {})
        self.backup_enabled.setChecked(bool(backup.get("automatic_enabled", False)))
        self._set_combo(self.backup_interval, backup.get("automatic_interval", "Wöchentlich"))
        self.backup_keep_count.setValue(int(backup.get("keep_count", 10)))
        self.backup_include_config.setChecked(bool(backup.get("include_config", True)))
        self.backup_include_database.setChecked(bool(backup.get("include_database", True)))
        self.backup_include_logs.setChecked(bool(backup.get("include_logs", False)))
        self.backup_include_downloads.setChecked(bool(backup.get("include_downloads", False)))

        ui = data.get("ui", {})
        self._set_combo(self.start_page, ui.get("start_page", "Dashboard"))
        self.confirm_restore.setChecked(bool(ui.get("confirm_before_restore", True)))

        self._loading = False
        self.refresh_tools()

    def save_settings(self):
        data = {
            "paths": {
                "downloads_dir": self.path_downloads.text().strip(),
                "finished_dir": self.path_finished.text().strip(),
                "work_dir": self.path_work.text().strip(),
                "backup_dir": self.path_backups.text().strip(),
                "logs_dir": self.path_logs.text().strip(),
                "tools_dir": self.path_tools.text().strip(),
            },
            "download": {
                "default_profile": self.default_profile.currentText(),
                "default_container": self.default_container.currentText(),
                "default_resolution": self.default_resolution.currentText(),
                "default_audio_format": self.default_audio.currentText(),
                "audio_only": self.default_audio_only.isChecked(),
                "clean_work_folder": self.default_clean_work.isChecked(),
            },
            "plex": {
                "create_nfo": self.create_nfo.isChecked(),
                "create_poster": self.create_poster.isChecked(),
                "create_fanart": self.create_fanart.isChecked(),
                "playlist_folder_mode": self.playlist_folder_mode.currentText(),
            },
            "backup": {
                "automatic_enabled": self.backup_enabled.isChecked(),
                "automatic_interval": self.backup_interval.currentText(),
                "keep_count": self.backup_keep_count.value(),
                "include_config": self.backup_include_config.isChecked(),
                "include_database": self.backup_include_database.isChecked(),
                "include_logs": self.backup_include_logs.isChecked(),
                "include_downloads": self.backup_include_downloads.isChecked(),
            },
            "ui": {
                "start_page": self.start_page.currentText(),
                "confirm_before_restore": self.confirm_restore.isChecked(),
            },
        }

        for folder in data["paths"].values():
            if folder:
                Path(folder).mkdir(parents=True, exist_ok=True)

        self.settings_service.save(data)
        QMessageBox.information(self, "Einstellungen", "Einstellungen wurden gespeichert.")

    def reset_settings(self):
        answer = QMessageBox.question(
            self,
            "Standardwerte",
            "Globale Einstellungen wirklich auf Standardwerte zurücksetzen?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.settings_service.reset()
        self.load_settings()

    def refresh_tools(self):
        if self.tool_service is None:
            self.tool_status.setText("Kein Tool-Service verbunden.")
            return
        tools = self.tool_service.check_tools()
        versions = self.tool_service.get_tool_versions()
        lines = []
        for name, exists in tools.items():
            lines.append(f"{'✓' if exists else '✗'} {name}")
        lines.append("")
        for name, version in versions.items():
            lines.append(f"{name}: {version}")
        self.tool_status.setText("\n".join(lines))

    def _choose_folder(self, edit: QLineEdit):
        start = edit.text().strip() or str(self.base_dir)
        folder = QFileDialog.getExistingDirectory(self, "Ordner auswählen", start)
        if folder:
            edit.setText(folder)

    def _open_folder(self, folder: str):
        path = Path(folder).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _set_combo(self, combo: QComboBox, value: str):
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)
