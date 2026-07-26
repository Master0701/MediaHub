from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.mediahub.services.ai_node_service import AINodeService
from src.mediahub.services.ai_node_provisioning_service import (
    AINodeInstallationState,
    AINodeProvisioningError,
    AINodeProvisioningService,
)
from src.mediahub.services.ai_node_ssh_setup_service import (
    AINodeSSHSetupError,
    AINodeSSHSetupService,
)
from src.mediahub.services.profile_service import ProfileService
from src.mediahub.services.settings_service import SettingsService


class GlobalSettingsPanel(QWidget):
    """Programmweite Einstellungen.

    Wichtig: Kanalspezifische Optionen bleiben im rechten Bereich der Kanalseite.
    Diese Seite ist für globale Pfade, Defaults, Backup, KI und Tool-Status gedacht.
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
        self._build_ai_connections_group()
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
        self.default_resolution.addItems(
            ["Beste", "4K", "1440p", "1080p", "720p", "480p"]
        )
        self.default_audio = QComboBox()
        self.default_audio.addItems(["M4A", "MP3", "AAC", "FLAC", "OGG", "WAV"])
        self.default_audio_only = QCheckBox(
            "Neue Kanäle standardmäßig als Audio laden"
        )
        self.default_clean_work = QCheckBox(
            "Arbeitsordner nach Import standardmäßig leeren"
        )

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

    def _build_ai_connections_group(self):
        group = QGroupBox("KI-Verbindungen")
        layout = QFormLayout(group)

        self.ai_local_enabled = QCheckBox(
            "Lokalen MediaHub-KI-Assistenten verwenden"
        )
        self.ai_node_enabled = QCheckBox("Raspberry-Pi-AI-Node verwenden")

        self.ai_node_host = QLineEdit()
        self.ai_node_host.setPlaceholderText(
            "z. B. 192.168.1.75 oder mediahub-pi"
        )

        self.ai_node_api_port = QSpinBox()
        self.ai_node_api_port.setRange(1, 65535)
        self.ai_node_api_port.setValue(8765)

        self.ai_node_api_token = QLineEdit()
        self.ai_node_api_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_node_api_token.setPlaceholderText("API-Token des AI-Nodes")

        self.ai_ssh_port = QSpinBox()
        self.ai_ssh_port.setRange(1, 65535)
        self.ai_ssh_port.setValue(22)

        self.ai_ssh_username = QLineEdit()
        self.ai_ssh_username.setPlaceholderText("z. B. mediahub")

        self.ai_ssh_password = QLineEdit()
        self.ai_ssh_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_ssh_password.setPlaceholderText(
            "Nur für diese Sitzung – wird nicht gespeichert"
        )

        self.ai_install_path = QLineEdit()
        self.ai_install_path.setText("/opt/mediahub/ai-node")

        self.ai_mode = QComboBox()
        self.ai_mode.addItems(
            [
                "Nur lokale MediaHub-KI",
                "Nur Raspberry-Pi-AI-Node",
                "Pi bevorzugen, lokal als Fallback",
                "Lokal bevorzugen, Pi als Zusatzknoten",
                "Beide automatisch verwenden",
            ]
        )

        self.ai_connection_status = QLabel("Noch nicht geprüft.")
        self.ai_connection_status.setWordWrap(True)

        self.btn_test_ai_node = QPushButton("AI-Node einrichten / Verbindung prüfen")
        self.btn_test_ai_node.setMinimumHeight(32)
        self.btn_test_ai_node.clicked.connect(self.test_ai_node_connection)

        layout.addRow("", self.ai_local_enabled)
        layout.addRow("", self.ai_node_enabled)
        layout.addRow("AI-Node-Adresse:", self.ai_node_host)
        layout.addRow("API-Port:", self.ai_node_api_port)
        layout.addRow("API-Token:", self.ai_node_api_token)
        layout.addRow("SSH-Port:", self.ai_ssh_port)
        layout.addRow("SSH-Benutzer:", self.ai_ssh_username)
        layout.addRow("SSH-Passwort:", self.ai_ssh_password)
        layout.addRow("Installationspfad:", self.ai_install_path)
        layout.addRow("Betriebsart:", self.ai_mode)
        layout.addRow("", self.btn_test_ai_node)
        layout.addRow("Status:", self.ai_connection_status)

        note = QLabel(
            "Das SSH-Passwort wird nicht gespeichert. "
            "Der lokale MediaHub-KI-Assistent und der Raspberry-Pi-AI-Node "
            "können unabhängig oder gemeinsam verwendet werden."
        )
        note.setWordWrap(True)
        layout.addRow("", note)

        self.content_layout.addWidget(group)

    def test_ai_node_connection(self):
        self.btn_test_ai_node.setEnabled(False)
        self.ai_connection_status.setText(
            "Verbindung wird geprüft ..."
        )

        host = self.ai_node_host.text().strip()
        ssh_password = self.ai_ssh_password.text()
        username = (
            self.ai_ssh_username.text().strip()
            or "mediahub"
        )
        install_path = (
            self.ai_install_path.text().strip()
            or "/opt/mediahub/ai-node"
        )

        try:
            if not self.ai_node_enabled.isChecked():
                self.ai_connection_status.setText(
                    "Der Raspberry-Pi-AI-Node ist deaktiviert."
                )
                return

            if not host:
                self.ai_connection_status.setText(
                    "Bitte zuerst die AI-Node-Adresse eintragen."
                )
                return

            token = self.ai_node_api_token.text().strip()

            if not token:
                if not ssh_password:
                    self.ai_connection_status.setText(
                        "Kein API-Token in MediaHub gespeichert. "
                        "Bitte einmalig das SSH-Passwort eingeben."
                    )
                    return

                self.ai_connection_status.setText(
                    "AI-Node-Installation und Token werden geprüft ..."
                )

                provisioner = AINodeProvisioningService(
                    host=host,
                    ssh_port=self.ai_ssh_port.value(),
                    username=username,
                    password=ssh_password,
                    project_dir=install_path,
                    timeout=15.0,
                )
                status = provisioner.inspect()

                if (
                    status.state
                    is AINodeInstallationState.SOFTWARE_MISSING
                ):
                    self.ai_connection_status.setText(
                        "MediaHub-AI-Node wird automatisch installiert ..."
                    )
                elif (
                    status.state
                    is AINodeInstallationState.SERVICE_STOPPED
                ):
                    self.ai_connection_status.setText(
                        "Der AI-Node-Dienst wird automatisch repariert ..."
                    )
                else:
                    self.ai_connection_status.setText(
                        "API-Token und AI-Node werden geprüft ..."
                    )

                result = provisioner.ensure_ready()
                token = result.api_token
                self.ai_node_api_token.setText(token)

                data = self.settings_service.load()
                if not isinstance(data, dict):
                    data = {}

                ai = data.get("ai")
                if not isinstance(ai, dict):
                    ai = {}

                ai.update(
                    {
                        "node_enabled": True,
                        "node_host": host,
                        "api_port": self.ai_node_api_port.value(),
                        "api_token": token,
                        "ssh_port": self.ai_ssh_port.value(),
                        "ssh_username": username,
                        "install_path": install_path,
                        "mode": self.ai_mode.currentText(),
                    }
                )
                data["ai"] = ai
                self.settings_service.save(data)

            settings = {
                "ai": {
                    "node_enabled": True,
                    "node_host": host,
                    "api_port": self.ai_node_api_port.value(),
                    "api_token": token,
                    "ssh_port": self.ai_ssh_port.value(),
                    "ssh_username": username,
                    "install_path": install_path,
                }
            }

            service = AINodeService.from_settings(
                settings,
                timeout=8.0,
            )
            health = service.health()

            if not health.online:
                self.ai_connection_status.setText(
                    f"Keine Verbindung zum AI-Node: "
                    f"{health.message}"
                )
                return

            plugins = service.list_plugins()
            detected = (
                health.detected_plugins
                if health.detected_plugins is not None
                else len(plugins)
            )
            loaded = (
                health.loaded_plugins
                if health.loaded_plugins is not None
                else "?"
            )

            self.ai_connection_status.setText(
                "AI-Node online – "
                f"Version {health.version}; "
                f"{detected} Plugin(s) erkannt, "
                f"{loaded} geladen; "
                "API-Token und geschützter Zugriff verfügbar."
            )
        except AINodeProvisioningError as error:
            self.ai_connection_status.setText(
                f"AI-Node-Einrichtung fehlgeschlagen: {error}"
            )
        except Exception as error:
            self.ai_connection_status.setText(
                f"Verbindungsprüfung fehlgeschlagen: {error}"
            )
        finally:
            self.ai_ssh_password.clear()
            self.btn_test_ai_node.setEnabled(True)

    def _build_tools_group(self):
        group = QGroupBox("Tool-Status")
        layout = QVBoxLayout(group)

        self.tool_status = QLabel("Noch nicht geprüft.")
        self.tool_status.setWordWrap(True)
        layout.addWidget(self.tool_status)

        self.tool_columns_widget = QWidget()
        self.tool_columns_layout = QGridLayout(self.tool_columns_widget)
        self.tool_columns_layout.setContentsMargins(0, 0, 0, 0)
        self.tool_columns_layout.setHorizontalSpacing(28)
        self.tool_columns_layout.setVerticalSpacing(8)
        layout.addWidget(self.tool_columns_widget)

        row = QHBoxLayout()
        self.btn_check_tools = QPushButton("Tools prüfen")
        self.btn_open_tools = QPushButton("Tools-Ordner öffnen")
        self.btn_check_tools.setMinimumHeight(32)
        self.btn_open_tools.setMinimumHeight(32)
        self.btn_check_tools.clicked.connect(self.refresh_tools)
        self.btn_open_tools.clicked.connect(
            lambda: self._open_folder(self.path_tools.text())
        )
        row.addWidget(self.btn_check_tools)
        row.addWidget(self.btn_open_tools)
        row.addStretch(1)
        layout.addLayout(row)

        if self.tool_service is not None and hasattr(
            self.tool_service, "add_change_listener"
        ):
            self.tool_service.add_change_listener(self.refresh_tools)

        self.content_layout.addWidget(group)

    def _build_ui_group(self):
        group = QGroupBox("Oberfläche")
        layout = QFormLayout(group)

        self.start_page = QComboBox()
        self.start_page.addItems(
            [
                "Dashboard",
                "Kanäle",
                "Bibliothek",
                "Downloads",
                "Jobs",
                "Scheduler",
                "Statistik",
                "Recovery",
            ]
        )
        self.confirm_restore = QCheckBox(
            "Vor Wiederherstellung Sicherheitsabfrage anzeigen"
        )

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
        self._set_combo(
            self.default_profile, download.get("default_profile", "Plex")
        )
        self._set_combo(
            self.default_container, download.get("default_container", "MKV")
        )
        self._set_combo(
            self.default_resolution, download.get("default_resolution", "1080p")
        )
        self._set_combo(
            self.default_audio, download.get("default_audio_format", "M4A")
        )
        self.default_audio_only.setChecked(bool(download.get("audio_only", False)))
        self.default_clean_work.setChecked(
            bool(download.get("clean_work_folder", True))
        )

        plex = data.get("plex", {})
        self.create_nfo.setChecked(bool(plex.get("create_nfo", True)))
        self.create_poster.setChecked(bool(plex.get("create_poster", True)))
        self.create_fanart.setChecked(bool(plex.get("create_fanart", True)))
        self._set_combo(
            self.playlist_folder_mode,
            plex.get("playlist_folder_mode", "Nur Staffeln"),
        )

        backup = data.get("backup", {})
        self.backup_enabled.setChecked(
            bool(backup.get("automatic_enabled", False))
        )
        self._set_combo(
            self.backup_interval,
            backup.get("automatic_interval", "Wöchentlich"),
        )
        self.backup_keep_count.setValue(int(backup.get("keep_count", 10)))
        self.backup_include_config.setChecked(
            bool(backup.get("include_config", True))
        )
        self.backup_include_database.setChecked(
            bool(backup.get("include_database", True))
        )
        self.backup_include_logs.setChecked(
            bool(backup.get("include_logs", False))
        )
        self.backup_include_downloads.setChecked(
            bool(backup.get("include_downloads", False))
        )

        ai = data.get("ai", {})
        self.ai_local_enabled.setChecked(bool(ai.get("local_enabled", True)))
        self.ai_node_enabled.setChecked(bool(ai.get("node_enabled", False)))
        self.ai_node_host.setText(str(ai.get("node_host", "")))
        self.ai_node_api_port.setValue(int(ai.get("api_port", 8765)))
        self.ai_node_api_token.setText(str(ai.get("api_token", "")))
        self.ai_ssh_port.setValue(int(ai.get("ssh_port", 22)))
        self.ai_ssh_username.setText(str(ai.get("ssh_username", "mediahub")))
        self.ai_ssh_password.clear()
        self.ai_install_path.setText(
            str(ai.get("install_path", "/opt/mediahub/ai-node"))
        )
        self._set_combo(
            self.ai_mode,
            str(ai.get("mode", "Nur lokale MediaHub-KI")),
        )
        self.ai_connection_status.setText("Noch nicht geprüft.")

        ui = data.get("ui", {})
        self._set_combo(self.start_page, ui.get("start_page", "Dashboard"))
        self.confirm_restore.setChecked(
            bool(ui.get("confirm_before_restore", True))
        )

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
            "ai": {
                "local_enabled": self.ai_local_enabled.isChecked(),
                "node_enabled": self.ai_node_enabled.isChecked(),
                "node_host": self.ai_node_host.text().strip(),
                "api_port": self.ai_node_api_port.value(),
                "api_token": self.ai_node_api_token.text().strip(),
                "ssh_port": self.ai_ssh_port.value(),
                "ssh_username": self.ai_ssh_username.text().strip(),
                "install_path": self.ai_install_path.text().strip(),
                "mode": self.ai_mode.currentText(),
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
        QMessageBox.information(
            self, "Einstellungen", "Einstellungen wurden gespeichert."
        )

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

        try:
            statuses = self.tool_service.get_all_tool_statuses(
                include_versions=True
            )
        except Exception as error:
            self.tool_status.setText(
                f"Tool-Status konnte nicht geladen werden: {error}"
            )
            return

        while self.tool_columns_layout.count():
            item = self.tool_columns_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        installed = sum(1 for item in statuses if item.get("installed"))
        self.tool_status.setText(
            f"{installed} von {len(statuses)} Werkzeugen installiert. "
            "Nach jeweils 4 Werkzeugen beginnt rechts eine neue Liste."
        )

        for index, status in enumerate(statuses):
            column = index // 4
            row = index % 4
            installed_mark = "✓" if status.get("installed") else "✗"
            name = str(
                status.get("display_name")
                or status.get("tool_id")
                or "Unbekannt"
            )
            version = str(status.get("version") or "nicht geprüft")
            used_by = [str(value) for value in status.get("used_by") or []]
            usage = ", ".join(used_by) if used_by else "nicht verwendet"

            label = QLabel(
                f"<b>{installed_mark} {name}</b><br>"
                f"Version: {version}<br>"
                f"Benutzt von: {usage}"
            )
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setMinimumWidth(230)
            label.setAlignment(
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
            )
            self.tool_columns_layout.addWidget(label, row, column)

        for column in range((len(statuses) + 3) // 4):
            self.tool_columns_layout.setColumnStretch(column, 1)

    def _choose_folder(self, edit: QLineEdit):
        start = edit.text().strip() or str(self.base_dir)
        folder = QFileDialog.getExistingDirectory(
            self, "Ordner auswählen", start
        )
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
