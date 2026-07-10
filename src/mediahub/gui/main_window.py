import json
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtCore import Qt, QUrl

from src.mediahub.gui.app_theme import dark_theme
from src.mediahub.gui.channel_panel import ChannelPanel
from src.mediahub.gui.settings_panel import SettingsPanel
from src.mediahub.gui.global_settings_panel import GlobalSettingsPanel
from src.mediahub.gui.log_panel import LogPanel
from src.mediahub.gui.download_queue_panel import DownloadQueuePanel
from src.mediahub.gui.library_panel import LibraryPanel
from src.mediahub.gui.dashboard_panel import DashboardPanel
from src.mediahub.gui.job_queue_panel import JobQueuePanel
from src.mediahub.gui.scheduler_panel import SchedulerPanel
from src.mediahub.gui.health_check_panel import HealthCheckPanel
from src.mediahub.gui.statistics_panel import StatisticsPanel
from src.mediahub.gui.recovery_center import RecoveryCenter
from src.mediahub.gui.help_center import HelpCenter
from src.mediahub.gui.assistant_panel import AssistantPanel
from src.mediahub.gui.plugin_center import PluginCenter
from src.mediahub.gui.release_gate import open_release_assistant_with_gate
from src.mediahub.gui.video_selection_dialog import VideoSelectionDialog
from src.mediahub.gui.setup_wizard import SetupWizard

from src.mediahub.gui.managers.playlist_manager import PlaylistManager
from src.mediahub.gui.managers.download_manager import DownloadManager
from src.mediahub.gui.managers.preview_manager import PreviewManager
from src.mediahub.gui.managers.tool_manager import ToolManager
from src.mediahub.gui.managers.sync_manager import SyncManager
from src.mediahub.gui.managers.database_manager import DatabaseManager
from src.mediahub.gui.managers.library_manager import LibraryManager
from src.mediahub.gui.managers.statistics_manager import StatisticsManager
from src.mediahub.gui.managers.scheduler_manager import SchedulerManager
from src.mediahub.gui.managers.job_queue_manager import JobQueueManager
from src.mediahub.gui.managers.recovery_manager import RecoveryManager
from src.mediahub.gui.managers.assistant_manager import AssistantManager
from src.mediahub.gui.managers.help_manager import HelpManager

from src.mediahub.services.youtube_service import YouTubeService
from src.mediahub.services.playlist_service import PlaylistService
from src.mediahub.services.download_service import DownloadService
from src.mediahub.services.tool_service import ToolService
from src.mediahub.services.archive_service import ArchiveService
from src.mediahub.storage.repository import MediaRepository


APP_VERSION = "v1.0.1"


class MainWindow(QMainWindow):
    def __init__(self, controller, logger=None, repository=None):
        super().__init__()

        self.controller = controller
        self.logger = logger

        self.tool_manager = None
        self.playlist_manager = None
        self.download_manager = None
        self.preview_manager = None
        self.sync_manager = None
        self.database_manager = None
        self.library_manager = None
        self.statistics_manager = None
        self.scheduler_manager = None
        self.job_queue_manager = None
        self.recovery_manager = None
        self.assistant_manager = None
        self.help_manager = None

        self.scheduler_panel = None
        self.health_check_panel = None
        self.statistics_panel = None
        self.recovery_center = None
        self.help_center = None
        self.assistant_panel = None
        self.plugin_center = None

        self.base_dir = Path.cwd()
        self.tool_service = ToolService(self.base_dir)
        self.youtube_service = YouTubeService()
        self.playlist_service = PlaylistService(self.youtube_service)
        self.download_service = DownloadService(self.tool_service)
        self.archive_service = ArchiveService()
        self.repository = repository or MediaRepository(self.base_dir, logger=self.logger)
        self.repository.initialize()

        self.setWindowTitle(f"MediaHub {APP_VERSION}")
        self.resize(1220, 760)
        self.setMinimumSize(980, 560)
        self.setStyleSheet(dark_theme())

        self.build_menu()
        self.build_toolbar()
        self.build_layout()
        self.build_statusbar()
        self.build_managers()
        self.build_shortcuts()
        self.apply_tooltips()
        self.show_whats_new_once()

        self.channel_panel.btn_preview.clicked.connect(self.preview_current_channel)
        self.channel_panel.btn_download.clicked.connect(self.select_and_download_videos)

        self.channel_panel.update_current_info()
        self.check_tools_on_start()
        self.database_manager.write_startup_status()
        self.statistics_manager.refresh_dashboard()
        if self.job_queue_manager is not None:
            self.job_queue_manager.refresh()
        self.open_dashboard()
        self.update_status("Bereit")

    def build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("Datei")
        file_menu.addAction("Start-Assistent", self.open_setup_wizard)
        file_menu.addSeparator()
        action_exit = QAction("Beenden", self)
        action_exit.setShortcut(QKeySequence("Ctrl+Q"))
        action_exit.setToolTip("MediaHub schließen (Strg+Q).")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        channel_menu = menu.addMenu("Kanäle")
        action_new_channel = QAction("Neuer Kanal", self)
        action_new_channel.setShortcut(QKeySequence("Ctrl+N"))
        action_new_channel.setToolTip("Neuen Kanal anlegen (Strg+N).")
        action_new_channel.triggered.connect(lambda: self.channel_panel.add_channel())
        channel_menu.addAction(action_new_channel)
        channel_menu.addAction("Start-Assistent", self.open_setup_wizard)
        channel_menu.addAction("Kanal bearbeiten", lambda: self.channel_panel.edit_channel())
        channel_menu.addAction("Kanal löschen", lambda: self.channel_panel.remove_channel())
        channel_menu.addSeparator()
        channel_menu.addAction("Playlist-Manager", self.open_playlist_manager)

        tools_menu = menu.addMenu("Werkzeuge")
        tools_menu.addAction("Tool-Center", self.open_tool_center)
        tools_menu.addAction("Tools prüfen", self.check_tools_on_start)
        tools_menu.addSeparator()
        tools_menu.addAction("🖼 Bilddiagnose", self.open_image_diagnostics)
        tools_menu.addAction("🛠 Bildstruktur reparieren", self.rebuild_image_assets_from_gui)
        tools_menu.addAction("🔄 Alte Playlistbilder übernehmen", self.migrate_legacy_playlist_images_from_gui)
        tools_menu.addSeparator()
        tools_menu.addAction("Vorschau", self.preview_current_channel)
        tools_menu.addAction("Videos auswählen", self.select_and_download_videos)
        tools_menu.addAction("Playlists aus Manager laden", self.select_playlists_and_download)
        tools_menu.addAction("Kanal synchronisieren", self.sync_current_channel)
        tools_menu.addSeparator()
        tools_menu.addAction("Dashboard", self.open_dashboard)
        tools_menu.addAction("Bibliothek", self.open_library)
        tools_menu.addAction("Job-Queue", self.open_job_queue)
        tools_menu.addAction("Sync-Job anlegen", self.add_sync_job)
        tools_menu.addAction("Nächsten Job starten", self.run_next_job)
        tools_menu.addSeparator()
        tools_menu.addAction("Scheduler", self.open_scheduler)
        tools_menu.addAction("Recovery Center", self.open_recovery_center)
        tools_menu.addAction("Selbsttest", self.open_recovery_center)
        tools_menu.addAction("MediaHub Assistent", self.open_assistant)
        tools_menu.addAction("Plugin Center", self.open_plugin_center)
        tools_menu.addAction("Sync-Aufgabe anlegen", self.add_scheduler_sync_task)
        tools_menu.addAction("Sync+Download-Aufgabe anlegen", self.add_scheduler_sync_download_task)
        tools_menu.addAction("Sync+Auto-Download-Aufgabe anlegen", self.add_scheduler_sync_auto_download_task)
        tools_menu.addAction("Fällige Scheduler-Jobs erzeugen", self.create_due_scheduler_jobs)
        tools_menu.addAction("Scheduler jetzt prüfen", self.check_scheduler_now)
        tools_menu.addAction("Scheduler-Automatik umschalten", self.toggle_scheduler_automatic)
        tools_menu.addAction("Download-Warteschlange", self.open_download_queue)
        tools_menu.addAction("Download abbrechen", self.cancel_download)


        extras_menu = menu.addMenu("Extras")
        extras_menu.addAction("Release-Assistent", self.open_release_assistant)

        extras_menu = menu.addMenu("Extras")
        extras_menu.addAction("Release-Assistent", lambda: open_release_assistant_with_gate(self, self.base_dir, APP_VERSION))
        extras_menu.addSeparator()

        help_menu = menu.addMenu("Hilfe")
        action_help_center = QAction("Hilfe-Center", self)
        action_help_center.setShortcut(QKeySequence("F1"))
        action_help_center.setToolTip("Passende Hilfe zur aktuellen Seite öffnen (F1).")
        action_help_center.triggered.connect(self.open_context_help)
        help_menu.addAction(action_help_center)
        help_menu.addAction("MediaHub Assistent", self.open_assistant)
        help_menu.addAction("Anleitung", self.open_manual)
        help_menu.addAction("Erste Schritte", self.open_first_steps)
        help_menu.addAction("Changelog", self.open_changelog)
        help_menu.addAction("Versionshistorie", self.open_version_history)
        help_menu.addSeparator()
        help_menu.addAction("Log-Ordner öffnen", self.open_log_folder)
        help_menu.addAction("Systeminformationen", self.open_system_info)
        help_menu.addAction("Health Check", self.open_health_check)
        help_menu.addSeparator()
        help_menu.addAction("Über MediaHub", self.open_about_dialog)

    def build_toolbar(self):
        toolbar = QToolBar("Hauptwerkzeuge")
        toolbar.setMovable(False)

        actions = [
            ("Wizard", "Start-Assistent / geführte Einrichtung", self.open_setup_wizard),
            ("Neu", "Neuen Kanal anlegen", lambda: self.channel_panel.add_channel()),
            ("Bearbeiten", "Kanal bearbeiten", lambda: self.channel_panel.edit_channel()),
            ("Tools", "Tool-Center", self.open_tool_center),
            ("PM", "Playlist-Manager", self.open_playlist_manager),
            ("Vorschau", "Vorschau laden", self.preview_current_channel),
            ("Videos", "Videos auswählen", self.select_and_download_videos),
            ("Sync", "Aktiven Kanal synchronisieren", self.sync_current_channel),
            ("Stop", "Download abbrechen", self.cancel_download),
            ("Hilfe", "Hilfe-Center öffnen", self.open_help_center),
        ]
        for index, (text, tooltip, callback) in enumerate(actions):
            if index in (3, 5, 8):
                toolbar.addSeparator()
            action = QAction(text, self)
            action.setToolTip(tooltip)
            action.triggered.connect(callback)
            toolbar.addAction(action)
        self.addToolBar(toolbar)

    def build_layout(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.channel_panel = ChannelPanel(controller=self.controller, repository=self.repository)
        self.settings_panel = SettingsPanel()
        self.log_panel = LogPanel()
        self.download_queue_panel = DownloadQueuePanel()
        self.library_panel = LibraryPanel(repository=self.repository)
        self.dashboard_panel = DashboardPanel(repository=self.repository)
        self.job_queue_panel = JobQueuePanel(repository=self.repository)
        self.scheduler_panel = SchedulerPanel(repository=self.repository)
        self.health_check_panel = HealthCheckPanel()
        self.statistics_panel = StatisticsPanel(repository=self.repository)
        self.recovery_center = RecoveryCenter()
        self.help_center = HelpCenter(base_dir=self.base_dir)
        self.assistant_panel = AssistantPanel()
        self.plugin_center = PluginCenter(base_dir=self.base_dir, parent=self)
        self.plugin_center.open_plugin_callback = self.open_plugin_by_id

        self.channel_panel.channel_selected_callback = self.settings_panel.load_channel
        self.settings_panel.change_callback = self.on_settings_changed

        self.dashboard_panel.set_quick_actions({
            "channel": lambda: self.channel_panel.add_channel(),
            "playlist": self.open_playlist_manager,
            "downloads": self.open_download_queue,
            "backup": self.create_assistant_backup,
            "health": self.open_health_check,
            "settings": lambda: self._select_nav_page("Einstellungen"),
            "help": self.open_help_center,
            "assistant": self.open_assistant,
        })

        for widget in (
            self.channel_panel,
            self.settings_panel,
            self.log_panel,
            self.download_queue_panel,
            self.library_panel,
            self.dashboard_panel,
            self.job_queue_panel,
            self.scheduler_panel,
            self.health_check_panel,
            self.statistics_panel,
            self.recovery_center,
            self.help_center,
            self.assistant_panel,
            self.plugin_center,
        ):
            widget.setMinimumSize(0, 0)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("MediaHubNavigation")
        self.nav_list.setFixedWidth(190)
        self.nav_list.setSpacing(2)

        self.page_stack = QStackedWidget()
        self.pages = {}

        self._add_page("🏠 Dashboard", self.dashboard_panel)
        self._add_page("📺 Kanäle", self._build_channels_page())
        self._add_page("📚 Bibliothek", self.library_panel)
        self._add_page("⬇ Downloads", self.download_queue_panel)
        self._add_page("📋 Jobs", self.job_queue_panel)
        self._add_page("⏰ Scheduler", self.scheduler_panel)
        self._add_page("📈 Statistik", self.statistics_panel)
        self._add_page("🛟 Recovery", self.recovery_center)
        self._add_page("🤖 Assistent", self.assistant_panel)
        self._add_page("🔌 Plugins", self.plugin_center)
        self._add_page("🩺 Health Check", self.health_check_panel)
        self._add_page("🛠 Werkzeuge", self._build_tools_page())
        self._add_page("⚙ Einstellungen", self._build_settings_page())
        self._add_page("📄 Log", self.log_panel)
        self._add_page("❓ Hilfe", self.help_center)

        self.nav_list.currentRowChanged.connect(self._navigation_changed)
        self.nav_list.setCurrentRow(0)

        main_layout.addWidget(self.nav_list)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        main_layout.addWidget(self.page_stack, 1)
        self.setCentralWidget(main_widget)

    def _add_page(self, title, widget):
        item = QListWidgetItem(title)
        item.setSizeHint(item.sizeHint())
        self.nav_list.addItem(item)
        self.page_stack.addWidget(widget)
        self.pages[title] = widget

    def _navigation_changed(self, index):
        if index < 0:
            return
        self.page_stack.setCurrentIndex(index)
        title = self.nav_list.item(index).text()
        if "Dashboard" in title and self.statistics_manager is not None:
            self.statistics_manager.refresh_dashboard()
        elif "Bibliothek" in title and self.library_manager is not None:
            # Die Bibliothek nicht bei jedem Seitenwechsel erneut komplett laden.
            # Ein Neuladen erfolgt weiterhin:
            # - beim ersten Öffnen,
            # - nach Downloads/Sync,
            # - über F5 oder den Aktualisieren-Button.
            if not getattr(self.library_panel, "_loaded_once", False):
                self.library_manager.refresh()
        elif "Jobs" in title and self.job_queue_manager is not None:
            self.job_queue_manager.refresh()
        elif "Scheduler" in title and self.scheduler_manager is not None:
            self.scheduler_manager.refresh()
        elif "Statistik" in title and self.statistics_manager is not None:
            self.statistics_manager.refresh_statistics()
        elif "Recovery" in title and self.recovery_manager is not None:
            self.recovery_manager.refresh()
        elif "Assistent" in title and self.assistant_manager is not None:
            self.assistant_manager.refresh()
        elif "Plugins" in title and self.plugin_center is not None:
            self.plugin_center.refresh()

    def _select_nav_page(self, contains_text):
        for row in range(self.nav_list.count()):
            if contains_text in self.nav_list.item(row).text():
                self.nav_list.setCurrentRow(row)
                return

    def _build_channels_page(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        splitter.addWidget(self.channel_panel)
        splitter.addWidget(self.settings_panel)
        # Kanalbereich deutlich breiter, Einstellungen rechts kompakt.
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([760, 300])
        return splitter

    def _build_statistics_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        title = QLabel("📈 Statistiken")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "Statistik-Seite für MediaHub.\n\n"
            "Die Datenbasis ist bereits in SQLite vorhanden.\n"
            "Diagramme für Downloads pro Tag, neue Videos pro Woche, größte Kanäle "
            "und häufigste Downloads folgen im nächsten Feinschliff-Build."
        )
        layout.addWidget(title)
        layout.addWidget(text, 1)
        return widget

    def _build_tools_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        title = QLabel("🛠 Werkzeuge")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        buttons = [
            ("Tool-Center öffnen", self.open_tool_center),
            ("Tools prüfen", self.check_tools_on_start),
            ("Health Check", self.open_health_check),
            ("Recovery Center", self.open_recovery_center),
            ("Health-Check-Seite öffnen", lambda: self._select_nav_page("Health Check")),
            ("Log-Ordner öffnen", self.open_log_folder),
            ("Plugin Center öffnen", self.open_plugin_center),
        ]
        for text, callback in buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)
            layout.addWidget(button)
        layout.addStretch(1)
        return widget

    def _build_settings_page(self):
        return GlobalSettingsPanel(self.base_dir, self.tool_service, self)

    def _build_help_page(self):
        return self.help_center

    def build_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def build_managers(self):
        self.tool_manager = ToolManager(
            main_window=self,
            tool_service=self.tool_service,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
        )

        self.download_manager = DownloadManager(
            main_window=self,
            download_service=self.download_service,
            tool_service=self.tool_service,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
            queue_panel=self.download_queue_panel,
        )

        self.preview_manager = PreviewManager(
            main_window=self,
            controller=self.controller,
            youtube_service=self.youtube_service,
            archive_service=self.archive_service,
            playlist_service=self.playlist_service,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
            can_start_download_callback=self.can_start_download,
            open_video_selection_callback=self.open_video_selection,
        )

        self.playlist_manager = PlaylistManager(
            main_window=self,
            controller=self.controller,
            youtube_service=self.youtube_service,
            playlist_service=self.playlist_service,
            archive_service=self.archive_service,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
            can_start_download_callback=self.can_start_download,
            open_video_selection_callback=self.open_video_selection,
        )

        self.sync_manager = SyncManager(
            main_window=self,
            controller=self.controller,
            youtube_service=self.youtube_service,
            repository=self.repository,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
        )

        self.database_manager = DatabaseManager(repository=self.repository, log_panel=self.log_panel)
        if self.health_check_panel is not None:
            self.health_check_panel.set_check_callback(self._run_health_check)
        self.library_manager = LibraryManager(library_panel=self.library_panel)
        self.statistics_manager = StatisticsManager(
            repository=self.repository,
            dashboard_panel=self.dashboard_panel,
            statistics_panel=self.statistics_panel,
        )
        self.job_queue_manager = JobQueueManager(
            repository=self.repository,
            job_queue_panel=self.job_queue_panel,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
            controller=self.controller,
            sync_manager=self.sync_manager,
            main_window=self,
            refresh_callbacks=[
                self.channel_panel.update_current_info,
                self.library_manager.refresh,
                self.statistics_manager.refresh_dashboard,
                self.statistics_manager.refresh_statistics,
            ],
        )
        self.recovery_manager = RecoveryManager(
            base_dir=self.base_dir,
            app_version=APP_VERSION,
            recovery_center=self.recovery_center,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
            logger=self.logger,
            repository=self.repository,
        )
        self.scheduler_manager = SchedulerManager(
            repository=self.repository,
            log_panel=self.log_panel,
            job_queue_manager=self.job_queue_manager,
            scheduler_panel=self.scheduler_panel,
            controller=self.controller,
            update_status_callback=self.update_status,
            recovery_manager=self.recovery_manager,
        )

        self.assistant_manager = AssistantManager(
            base_dir=self.base_dir,
            tool_service=self.tool_service,
            repository=self.repository,
            scheduler_manager=self.scheduler_manager,
            recovery_manager=self.recovery_manager,
            assistant_panel=self.assistant_panel,
            dashboard_panel=self.dashboard_panel,
            log_panel=self.log_panel,
            update_status_callback=self.update_status,
        )
        self.assistant_manager.refresh()

        self.help_manager = HelpManager(self)
        self.help_center.set_callbacks(self.help_manager.callbacks())

    def build_shortcuts(self):
        """Zentrale Tastenkürzel für den täglichen Workflow."""
        shortcuts = [
            ("F1", self.open_context_help),
            ("F5", self.refresh_current_page),
            ("Ctrl+B", self.create_assistant_backup),
            ("Ctrl+E", lambda: self._select_nav_page("Einstellungen")),
            ("Ctrl+L", lambda: self._select_nav_page("Log")),
            ("Ctrl+Shift+H", self.open_health_check),
        ]
        for sequence, callback in shortcuts:
            action = QAction(self)
            action.setShortcut(QKeySequence(sequence))
            action.triggered.connect(callback)
            self.addAction(action)

    def apply_tooltips(self):
        """Wichtige Bereiche bekommen kurze Erklärungen, ohne das Layout zu verändern."""
        nav_tips = {
            "Dashboard": "Startübersicht mit Status, Assistent und Schnellaktionen.",
            "Kanäle": "YouTube-Kanäle verwalten und Download-Einstellungen pro Kanal ändern.",
            "Bibliothek": "Bekannte Videos und Downloadstatus aus der Datenbank anzeigen.",
            "Downloads": "Aktuelle und letzte Downloads in der Warteschlange prüfen.",
            "Jobs": "Automatische Sync- und Download-Jobs anzeigen und starten.",
            "Scheduler": "Wiederkehrende Aufgaben und automatische Backups planen.",
            "Statistik": "Statistiken zu Kanälen, Videos, Downloads und Datenbank anzeigen.",
            "Recovery": "Backups, Wiederherstellung und Wartungsfunktionen.",
            "Assistent": "Health Score, Empfehlungen und schnelle Problemlösungen.",
            "Plugins": "Vorbereitete Erweiterungen und Plugin-Manifestdateien anzeigen.",
            "Health Check": "Werkzeuge, Ordner, Datenbank und Grundsystem prüfen.",
            "Werkzeuge": "Tool-Center, externe Programme und Log-Ordner.",
            "Einstellungen": "Globale Pfade, Backup-Vorgaben, Plex und Tool-Status.",
            "Log": "Laufende Meldungen und Fehlerprotokoll.",
            "Hilfe": "Interaktive Hilfe, Suche und PDF-Handbuch.",
        }
        for row in range(self.nav_list.count()):
            item = self.nav_list.item(row)
            title = item.text()
            for key, tip in nav_tips.items():
                if key in title:
                    item.setToolTip(tip)
                    break

        button_tips = {
            "btn_preview": "Lädt eine Vorschau der Videos für den aktuell ausgewählten Kanal.",
            "btn_download": "Öffnet die Videoauswahl und startet ausgewählte Downloads.",
        }
        for name, tip in button_tips.items():
            widget = getattr(self.channel_panel, name, None)
            if widget is not None:
                widget.setToolTip(tip)

        self.status.setToolTip("Statusleiste: zeigt letzte Aktion, geladene Kanäle und Programmzustand.")

    def refresh_current_page(self):
        """F5 aktualisiert die aktuell sichtbare Seite."""
        title = self.nav_list.currentItem().text() if self.nav_list.currentItem() else ""

        if "Bibliothek" in title and self.library_manager is not None:
            self.library_manager.refresh()
        else:
            self._navigation_changed(self.nav_list.currentRow())

        if "Dashboard" in title and self.assistant_manager is not None:
            self.assistant_manager.refresh()
        self.update_status(f"Aktualisiert: {title.replace('🏠 ', '').replace('📺 ', '').replace('📚 ', '')}")

    def open_context_help(self):
        """F1 öffnet die passende Hilfeseite zum aktuellen Bereich."""
        title = self.nav_list.currentItem().text() if self.nav_list.currentItem() else ""
        topic_map = {
            "Dashboard": "dashboard",
            "Kanäle": "channels",
            "Bibliothek": "library",
            "Downloads": "downloads",
            "Jobs": "downloads",
            "Scheduler": "scheduler",
            "Statistik": "statistics",
            "Recovery": "recovery",
            "Assistent": "assistant",
            "Health Check": "health",
            "Plugins": "tools",
            "Werkzeuge": "tools",
            "Einstellungen": "settings",
            "Log": "faq",
            "Hilfe": "faq",
        }
        key = "faq"
        for fragment, topic_key in topic_map.items():
            if fragment in title:
                key = topic_key
                break
        if hasattr(self.help_center, "select_topic"):
            self.help_center.select_topic(key)
        self.open_help_center()
        self.update_status("Hilfe geöffnet")

    def show_whats_new_once(self):
        """Zeigt die Versionshinweise einmal pro Version."""
        config_dir = self.base_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        state_file = config_dir / "ui_state.json"
        state = {}
        try:
            if state_file.exists():
                state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            state = {}

        if state.get("last_whats_new") == APP_VERSION:
            return

        QMessageBox.information(
            self,
            "Was ist neu?",
            f"MediaHub {APP_VERSION}\n\n"
            "Neu in v1.0.1:\n"
            "• Lokale Videos und Ordner wieder direkt aus der Bibliothek öffnen.\n"
            "• Downloads werden zuverlässig mit Dateipfad in SQLite gespeichert.\n"
            "• Bibliothek lädt beim Seitenwechsel nicht mehr unnötig neu.\n"
            "• Kanalbereich und Kanalinformationen übersichtlicher dargestellt.",
        )
        state["last_whats_new"] = APP_VERSION
        try:
            state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def open_setup_wizard(self):
        wizard = SetupWizard(
            controller=self.controller,
            youtube_service=self.youtube_service,
            playlist_service=self.playlist_service,
            repository=self.repository,
            sync_manager=self.sync_manager,
            job_queue_manager=self.job_queue_manager,
            scheduler_manager=self.scheduler_manager,
            parent=self,
        )

        if wizard.exec():
            self.channel_panel.refresh_list()
            if getattr(wizard, "created_index", None) is not None:
                self.channel_panel.channel_list.setCurrentRow(wizard.created_index)
            self.channel_panel.update_current_info()
            self.settings_panel.load_channel(self.controller.get_current_channel())
            self.library_manager.refresh()
            self.statistics_manager.refresh_dashboard()
            if self.job_queue_manager is not None:
                self.job_queue_manager.refresh()
            if self.scheduler_manager is not None:
                self.scheduler_manager.refresh()
            self.log_panel.write("Start-Assistent abgeschlossen.")
            self.update_status("Start-Assistent abgeschlossen")

            start_mode = getattr(wizard, "start_after_save", "")
            if start_mode == "sync_download":
                self.sync_and_download_new_for_channel(wizard.created_channel)
            elif start_mode == "sync":
                self.sync_manager.sync_channel(wizard.created_channel)
                self.channel_panel.update_current_info()
                self.library_manager.refresh()
                self.statistics_manager.refresh_dashboard()


    def open_release_assistant(self):
        open_release_assistant_with_gate(self, self.base_dir, APP_VERSION)

    def open_tool_center(self):
        self.tool_manager.open_tool_center()

    def check_tools_on_start(self):
        self.tool_manager.check_tools_on_start()

    def open_playlist_manager(self):
        self.playlist_manager.open_playlist_manager()

    def select_playlists_and_download(self):
        self.playlist_manager.select_playlists_and_download()

    def sync_current_channel(self):
        self.sync_manager.sync_current_channel()
        self.channel_panel.update_current_info()
        self.library_manager.refresh()
        self.statistics_manager.refresh_dashboard()

    def sync_and_download_new_for_channel(self, channel):
        if channel is None:
            self.log_panel.write("Wizard: Kein Kanal für Sync/Download vorhanden.")
            self.update_status("Kein Kanal")
            return

        self.log_panel.write(f"Wizard: Sync gestartet für {channel.name}")
        result = self.sync_manager.sync_channel(channel)
        self.channel_panel.update_current_info()
        self.library_manager.refresh()
        self.statistics_manager.refresh_dashboard()

        if not result.get("ok", False) and int(result.get("failed", 0) or 0) > 0:
            self.log_panel.write("Wizard: Sync hatte Fehler. Download-Auswahl wird trotzdem live vorbereitet.")

        videos = []

        # Teil 9: Die direkte Auswahl nach dem Assistenten nutzt bewusst
        # denselben Live-Weg wie der normale Video-Button. Sonst landen je nach
        # yt-dlp/SQLite-Zwischenstand wieder Platzhalter wie "Kanalvideo" oder
        # "Ohne Titel" in der Auswahl.
        try:
            if self.preview_manager.has_active_playlist_settings(channel):
                self.log_panel.write("Wizard: Lade aktive Playlists live für die Videoauswahl.")
                videos = self.preview_manager.load_active_playlist_videos(channel, limit=None)
            else:
                video_url = self.preview_manager.to_videos_url(channel.url)
                self.log_panel.write(f"Wizard: Lade Kanalvideos live: {video_url}")
                videos = self.youtube_service.preview_channel(video_url, limit=None)
                videos = self.preview_manager.add_default_playlist_info(channel, videos)

            videos = self.archive_service.mark_videos(channel, videos)
            videos = self._filter_bad_wizard_video_rows(videos)
        except Exception as error:
            self.log_panel.write(f"Wizard: Live-Videoliste fehlgeschlagen: {error}")
            videos = []

        if not videos and self.repository is not None:
            self.log_panel.write("Wizard: Fallback auf Datenbank-Videos.")
            rows = self.repository.get_new_videos_for_channel(channel.name)
            for row in rows:
                if int(row.get("is_members_only", 0) or 0):
                    continue
                video_id = str(row.get("video_id", "") or "").strip()
                url = row.get("url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else "")
                videos.append({
                    "id": video_id,
                    "video_id": video_id,
                    "url": url,
                    "title": row.get("title", "Ohne Titel"),
                    "playlist": row.get("playlists", "") or getattr(channel, "name", "Kanalvideos"),
                    "playlist_original": row.get("playlists", "") or getattr(channel, "name", "Kanalvideos"),
                    "status": "Neu",
                    "checked": True,
                })
            videos = self._filter_bad_wizard_video_rows(videos)

        if not videos:
            self.log_panel.write("Wizard: Keine downloadbaren Videos gefunden.")
            self.update_status("Keine Videos")
            self.open_library()
            return

        self.log_panel.write(f"Wizard: {len(videos)} Video(s) für Download-Auswahl geladen.")
        self.open_video_selection(channel, videos)

    def _filter_bad_wizard_video_rows(self, videos):
        """Entfernt YouTube-/Playlist-Platzhalter aus jeder Videoauswahl."""
        cleaned = []
        bad_titles = {
            "", "ohne titel", "untitled", "none", "null", "nan",
            "kanalvideo", "channel video", "playlist", "playlists", "videos", "uploads",
            "deleted video", "private video", "[deleted video]", "[private video]",
        }
        seen = set()
        for video in videos or []:
            video_id = str(video.get("video_id") or video.get("id") or "").strip()
            title = str(video.get("title") or "").strip()
            url = str(video.get("url") or video.get("webpage_url") or "").strip()

            is_watch_url = ("watch?v=" in url) or ("youtu.be/" in url) or ("/shorts/" in url)
            if not video_id and not is_watch_url:
                continue
            if video_id and not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) and not is_watch_url:
                continue
            if title.lower() in bad_titles:
                continue

            key = video_id or url
            if key and key in seen:
                continue
            if key:
                seen.add(key)

            if not video.get("id") and video_id:
                video["id"] = video_id
            if not video.get("video_id") and video_id:
                video["video_id"] = video_id
            cleaned.append(video)
        return cleaned

    def sync_and_auto_download_new_for_channel(self, channel):
        if channel is None:
            self.log_panel.write("Automation: Kein Kanal für Sync/Auto-Download vorhanden.")
            self.update_status("Kein Kanal")
            return

        self.log_panel.write(f"Automation: Sync gestartet für {channel.name}")
        result = self.sync_manager.sync_channel(channel)
        self.channel_panel.update_current_info()
        self.library_manager.refresh()
        self.statistics_manager.refresh_dashboard()

        if not result.get("ok", False) and int(result.get("failed", 0) or 0) > 0:
            self.log_panel.write("Automation: Sync hatte Fehler. Neue bekannte Videos werden trotzdem geprüft.")

        if self.repository is None:
            self.log_panel.write("Automation: Keine Datenbank für neue Videos verfügbar.")
            return

        rows = self.repository.get_new_videos_for_channel(channel.name)
        videos = []
        skipped_members = 0
        for row in rows:
            if int(row.get("is_members_only", 0) or 0):
                skipped_members += 1
                continue
            video_id = row.get("video_id", "")
            videos.append({
                "id": video_id,
                "url": row.get("url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else ""),
                "title": row.get("title", "Ohne Titel"),
                "playlist": row.get("playlists", ""),
                "playlist_original": row.get("playlists", ""),
                "status": "Neu",
                "checked": True,
            })

        if skipped_members:
            self.log_panel.write(f"Automation: {skipped_members} Mitglieder-Video(s) übersprungen.")

        if not videos:
            self.log_panel.write("Automation: Keine neuen downloadbaren Videos gefunden.")
            self.update_status("Keine neuen Videos")
            self.open_library()
            return

        self.log_panel.write(f"Automation: Starte Download für {len(videos)} neue Video(s).")
        self.start_download_queue(channel, videos)

    def preview_current_channel(self):
        self.preview_manager.preview_current_channel()

    def select_and_download_videos(self):
        self.preview_manager.select_and_download_videos()

    def open_video_selection(self, channel, videos):
        if not videos:
            self.log_panel.write("Keine Videos gefunden.")
            self.update_status("Keine Videos gefunden")
            return

        # Teil 9 Fix 3: derselbe Schutz jetzt auch für den normalen Video-Button,
        # nicht nur für die direkte Wizard-Auswahl.
        if hasattr(self, "_filter_bad_wizard_video_rows"):
            before = len(videos)
            videos = self._filter_bad_wizard_video_rows(videos)
            removed = before - len(videos)
            if removed:
                self.log_panel.write(f"{removed} ungültige YouTube-Platzhalter ausgeblendet.")

        if not videos:
            self.log_panel.write("Keine echten Videos nach dem Platzhalter-Filter gefunden.")
            self.update_status("Keine Videos gefunden")
            return

        videos = self._apply_library_status_to_videos(videos)
        dialog = VideoSelectionDialog(videos, self)

        if not dialog.exec():
            self.log_panel.write("Videoauswahl abgebrochen.")
            self.update_status("Bereit")
            return

        selected_videos = dialog.selected_videos

        if not selected_videos:
            self.log_panel.write("Keine Videos ausgewählt.")
            self.update_status("Bereit")
            return

        self.start_download_queue(channel, selected_videos)

    def _apply_library_status_to_videos(self, videos):
        """Reichert frisch geladene Videolisten mit SQLite-Status an.

        Die Videoauswahl bekommt ihre Liste oft direkt von YouTube. Dadurch weiß
        sie ohne diesen Abgleich nicht, dass ein Video nach einem früheren
        Downloadversuch bereits als Mitglieder-Video in SQLite markiert wurde.
        """
        if not videos or self.repository is None:
            return videos

        video_ids = []
        for video in videos:
            video_id = str(video.get("video_id") or video.get("id") or "").strip()
            if video_id:
                video_ids.append(video_id)

        if not video_ids:
            return videos

        status_by_id = {}

        try:
            unique_ids = list(dict.fromkeys(video_ids))
            for start in range(0, len(unique_ids), 300):
                chunk = unique_ids[start:start + 300]
                placeholders = ",".join("?" for _ in chunk)
                rows = self.repository.database.fetch_all(
                    f"""
                    SELECT video_id, status, is_new, is_downloaded, is_members_only
                    FROM videos
                    WHERE video_id IN ({placeholders})
                    """,
                    tuple(chunk),
                )
                for row in rows:
                    data = dict(row)
                    status_by_id[str(data.get("video_id") or "")] = data
        except Exception as error:
            try:
                self.log_panel.write(f"Videoauswahl: SQLite-Status konnte nicht geladen werden: {error}")
            except Exception:
                pass
            return videos

        members_count = 0

        for video in videos:
            video_id = str(video.get("video_id") or video.get("id") or "").strip()
            db_row = status_by_id.get(video_id)

            if not db_row:
                continue

            is_members = int(db_row.get("is_members_only") or 0) == 1
            is_downloaded = int(db_row.get("is_downloaded") or 0) == 1
            is_new = int(db_row.get("is_new") or 0) == 1
            db_status = str(db_row.get("status") or "").strip()

            video["is_members_only"] = 1 if is_members else int(video.get("is_members_only") or 0)
            video["is_downloaded"] = 1 if is_downloaded else int(video.get("is_downloaded") or 0)
            video["is_new"] = 1 if is_new else int(video.get("is_new") or 0)

            if is_members:
                video["status"] = "members_only"
                members_count += 1
            elif is_downloaded:
                video["status"] = "Bereits geladen"
            elif db_status:
                video["status"] = db_status

        if members_count:
            try:
                self.log_panel.write(f"Videoauswahl: {members_count} bekannte Mitglieder-Video(s) markiert.")
            except Exception:
                pass

        return videos


    def can_start_download(self):
        return self.download_manager.can_start_download()

    def open_dashboard(self):
        if self.statistics_manager is not None:
            self.statistics_manager.refresh_dashboard()
        self._select_nav_page("Dashboard")

    def open_library(self):
        if self.library_manager is not None:
            self.library_manager.refresh()
        self._select_nav_page("Bibliothek")

    def open_job_queue(self):
        if self.job_queue_manager is not None:
            self.job_queue_manager.refresh()
        self._select_nav_page("Jobs")

    def open_scheduler(self):
        if self.scheduler_manager is not None:
            self.scheduler_manager.refresh()
        self._select_nav_page("Scheduler")

    def open_recovery_center(self):
        if self.recovery_manager is not None:
            self.recovery_manager.refresh()
        self._select_nav_page("Recovery")

    def create_assistant_backup(self):
        if self.assistant_manager is not None:
            self.assistant_manager.create_backup()
            if self.recovery_manager is not None:
                self.recovery_manager.refresh()
            self._select_nav_page("Recovery")

    def add_scheduler_sync_task(self):
        self.scheduler_manager.add_sync_task_for_current_channel()
        self.open_scheduler()

    def add_scheduler_sync_download_task(self):
        self.scheduler_manager.add_sync_download_task_for_current_channel()
        self.open_scheduler()

    def add_scheduler_sync_auto_download_task(self):
        self.scheduler_manager.add_sync_auto_download_task_for_current_channel()
        self.open_scheduler()

    def create_due_scheduler_jobs(self):
        self.scheduler_manager.create_due_jobs()
        self.open_job_queue()

    def check_scheduler_now(self):
        self.scheduler_manager.check_due_tasks_automatically()
        self.open_job_queue()

    def toggle_scheduler_automatic(self):
        self.scheduler_manager.toggle_automatic_checks()
        self.open_scheduler()

    def add_sync_job(self):
        self.job_queue_manager.add_sync_job_for_channel(self.controller.get_current_channel())
        self.open_job_queue()

    def run_next_job(self):
        self.open_job_queue()
        self.job_queue_manager.run_next_pending_job()

    def open_download_queue(self):
        self._select_nav_page("Downloads")
        self.download_manager.open_queue_dialog()

    def cancel_download(self):
        self.download_manager.cancel_download()

    def start_download_queue(self, channel, videos):
        if self.job_queue_manager is not None:
            self.job_queue_manager.add_download_job_for_channel(channel, len(videos or []))
        self._select_nav_page("Downloads")
        self.download_manager.start_download_queue(channel, videos)
        self.channel_panel.update_current_info()
        self.library_manager.refresh()
        self.statistics_manager.refresh_dashboard()

    def on_settings_changed(self, **changes):
        self.controller.update_current_channel(**changes)
        self.channel_panel.update_current_info()
        self.settings_panel.load_channel(self.controller.get_current_channel())
        self.log_panel.write("Einstellungen gespeichert.")
        self.update_status("Einstellungen gespeichert")

    def open_assistant(self):
        self._select_nav_page("Assistent")
        if self.assistant_manager is not None:
            self.assistant_manager.refresh()

    def open_plugin_center(self):
        if self.plugin_center is not None:
            self.plugin_center.refresh()
        self._select_nav_page("Plugins")

    def open_plugin_by_id(self, plugin_id):
        QMessageBox.information(
            self,
            "Plugin",
            f"Dieses Plugin ist in MediaHub v1.0 noch nicht als ausführbares Plugin verfügbar:\n{plugin_id}"
        )

    def open_help_center(self):
        self._select_nav_page("Hilfe")

    def open_manual(self):
        manual = self.base_dir / "docs" / "MediaHub_Anleitung.pdf"
        if not manual.exists():
            QMessageBox.warning(self, "Anleitung", f"Die Anleitung wurde nicht gefunden:\n{manual}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual)))

    def open_first_steps(self):
        QMessageBox.information(
            self,
            "Erste Schritte",
            "1. Start-Assistent öffnen.\n"
            "2. YouTube-URL eintragen.\n"
            "3. Kanalname, Arbeitsordner und Zielordner prüfen.\n"
            "4. Playlists auswählen.\n"
            "5. Dateinamenschema kontrollieren.\n"
            "6. Speichern und starten.\n\n"
            "Danach synchronisiert MediaHub den Kanal und öffnet die Videoauswahl, "
            "wenn neue downloadbare Videos gefunden wurden.",
        )

    def open_changelog(self):
        path = self.base_dir / "CHANGELOG.md"
        if not path.exists():
            QMessageBox.warning(self, "Changelog", "CHANGELOG.md wurde nicht gefunden.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_version_history(self):
        """Öffnet die Versionshistorie im Hilfe-Center."""
        if self.help_center is not None and hasattr(self.help_center, "select_topic"):
            self.help_center.select_topic("version_history")
        self.open_help_center()
        self.update_status("Versionshistorie geöffnet")

    def open_image_diagnostics(self):
        report = self._build_image_diagnostics_report()
        self._show_text_dialog("MediaHub Bilddiagnose", report, width=900, height=650)
        self.update_status("Bilddiagnose geöffnet")

    def rebuild_image_assets_from_gui(self):
        result = self._rebuild_image_assets()
        text = (
            "Bildstruktur repariert.\n\n"
            f"Kanalordner geprüft: {result['channels']}\n"
            f"Playlist-Ordner angelegt: {result['playlist_dirs_created']}\n"
            f"images.json geschrieben: {result['indexes_written']}\n\n"
            "Es wurde nichts gelöscht."
        )
        QMessageBox.information(self, "Bildstruktur repariert", text)
        self.update_status("Bildstruktur repariert")

    def migrate_legacy_playlist_images_from_gui(self):
        result = self._migrate_legacy_playlist_images(move=False)
        text = (
            "Alte Playlistbilder wurden übernommen.\n\n"
            f"Kanalordner geprüft: {result['channels']}\n"
            f"Playlistbilder übernommen: {result['copied']}\n"
            f"Übersprungen: {result['skipped']}\n"
            f"images.json geschrieben: {result['indexes_written']}\n\n"
            "Die alten Dateien wurden kopiert, nicht gelöscht."
        )
        QMessageBox.information(self, "Playlistbilder übernommen", text)
        self.update_status("Playlistbilder übernommen")

    def _show_text_dialog(self, title: str, text: str, width: int = 760, height: int = 520):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(width, height)

        layout = QVBoxLayout(dialog)
        box = QTextEdit()
        box.setReadOnly(True)
        box.setPlainText(text)

        close_button = QPushButton("Schließen")
        close_button.clicked.connect(dialog.accept)

        layout.addWidget(box, 1)
        layout.addWidget(close_button)
        dialog.exec()

    def _build_image_diagnostics_report(self) -> str:
        lines = []
        assets_dir = self.base_dir / "assets" / "channels"

        def file_info(path: Path) -> str:
            if not path.exists():
                return "FEHLT"
            if path.is_dir():
                return "ORDNER"
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            if size >= 1024 * 1024:
                return f"OK ({size / (1024 * 1024):.1f} MB)"
            if size >= 1024:
                return f"OK ({size / 1024:.1f} KB)"
            return f"OK ({size} B)"

        lines.append("MediaHub Bilddiagnose")
        lines.append(f"Root: {self.base_dir}")
        lines.append("")
        lines.append("=" * 70)
        lines.append("Lokale MediaHub-Bilder")
        lines.append("=" * 70)
        lines.append(f"Ordner: {assets_dir}")

        if not assets_dir.exists():
            lines.append("❌ assets/channels existiert nicht.")
            return "\n".join(lines)

        channel_dirs = [p for p in sorted(assets_dir.iterdir()) if p.is_dir()]
        if not channel_dirs:
            lines.append("❌ Keine Kanal-Bildordner gefunden.")
            return "\n".join(lines)

        for channel_dir in channel_dirs:
            lines.append("")
            lines.append(f"Kanalordner: {channel_dir.name}")

            for filename in ("channel.jpg", "banner.jpg"):
                path = channel_dir / filename
                icon = "✅" if path.exists() else "⚠"
                lines.append(f"{icon} {filename}: {file_info(path)}")

            manifest = channel_dir / "images.json"
            icon = "✅" if manifest.exists() else "⚠"
            lines.append(f"{icon} images.json: {file_info(manifest)}")

            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    playlists = data.get("playlists", {})
                    lines.append(f"   Playlists im Manifest: {len(playlists)}")
                except Exception as error:
                    lines.append(f"   ⚠ images.json konnte nicht gelesen werden: {error}")

            playlist_dir = channel_dir / "playlists"
            if playlist_dir.exists():
                playlist_images = sorted(playlist_dir.glob("*.jpg"))
                lines.append(f"✅ playlist-Bilder: {len(playlist_images)}")
                for image in playlist_images[:25]:
                    lines.append(f"   - {image.name}: {file_info(image)}")
                if len(playlist_images) > 25:
                    lines.append(f"   ... {len(playlist_images) - 25} weitere")
            else:
                lines.append("⚠ playlists-Ordner fehlt")

        lines.append("")
        lines.append("Hinweis:")
        lines.append("Diese Diagnose verändert keine Dateien.")
        return "\n".join(lines)

    def _write_image_index(self, channel_dir: Path):
        playlists_dir = channel_dir / "playlists"
        playlists_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "channel": "channel.jpg" if (channel_dir / "channel.jpg").exists() else "",
            "banner": "banner.jpg" if (channel_dir / "banner.jpg").exists() else "",
            "playlists": {},
        }

        for path in sorted(playlists_dir.glob("*.jpg")):
            data["playlists"][path.stem] = f"playlists/{path.name}"

        (channel_dir / "images.json").write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

    def _rebuild_image_assets(self) -> dict:
        assets_dir = self.base_dir / "assets" / "channels"
        assets_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "channels": 0,
            "playlist_dirs_created": 0,
            "indexes_written": 0,
        }

        for channel_dir in sorted(assets_dir.iterdir()):
            if not channel_dir.is_dir():
                continue

            result["channels"] += 1
            playlists_dir = channel_dir / "playlists"
            if not playlists_dir.exists():
                playlists_dir.mkdir(parents=True, exist_ok=True)
                result["playlist_dirs_created"] += 1

            self._write_image_index(channel_dir)
            result["indexes_written"] += 1

        return result

    def _migrate_legacy_playlist_images(self, move: bool = False) -> dict:
        assets_dir = self.base_dir / "assets" / "channels"
        assets_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "channels": 0,
            "copied": 0,
            "skipped": 0,
            "indexes_written": 0,
        }

        for channel_dir in sorted(assets_dir.iterdir()):
            if not channel_dir.is_dir():
                continue

            result["channels"] += 1
            playlists_dir = channel_dir / "playlists"
            playlists_dir.mkdir(parents=True, exist_ok=True)

            for source in sorted(channel_dir.glob("playlist_*.jpg")):
                playlist_id = source.stem.replace("playlist_", "", 1).strip()
                if not playlist_id:
                    result["skipped"] += 1
                    continue

                target = playlists_dir / f"{playlist_id}.jpg"
                if target.exists():
                    result["skipped"] += 1
                    continue

                if move:
                    shutil.move(str(source), str(target))
                else:
                    shutil.copy2(str(source), str(target))

                result["copied"] += 1

            self._write_image_index(channel_dir)
            result["indexes_written"] += 1

        return result


    def open_log_folder(self):
        path = self.base_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_system_info(self):
        QMessageBox.information(self, "Systeminformationen", self._system_info_text())

    def open_health_check(self):
        if self.health_check_panel is not None:
            self.health_check_panel.refresh()
            self._select_nav_page("Health Check")
            return
        checks = self._run_health_check()
        text = "MediaHub Health Check\n\n" + "\n".join(checks)
        QMessageBox.information(self, "Health Check", text)

    def open_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Über MediaHub")
        dialog.resize(520, 430)
        layout = QVBoxLayout(dialog)

        title = QLabel("MediaHub")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        version = QLabel(f"Version {APP_VERSION}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(
            "Ein Programm zur Verwaltung, Synchronisierung und Automatisierung\n"
            "von YouTube-Kanälen, Playlists und Mediendownloads."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        credits = QGroupBox("Projekt")
        form = QFormLayout(credits)
        form.addRow("Idee:", QLabel("Shadow1racer"))
        form.addRow("Programmdesign und Entwicklung:", QLabel("Master2511"))
        form.addRow("KI-Unterstützung:", QLabel("ChatGPT (OpenAI)"))

        system = QTextEdit()
        system.setReadOnly(True)
        system.setMaximumHeight(120)
        system.setPlainText(self._system_info_text())

        close_button = QPushButton("Schließen")
        close_button.clicked.connect(dialog.accept)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(description)
        layout.addWidget(credits)
        layout.addWidget(QLabel("System:"))
        layout.addWidget(system)
        layout.addWidget(close_button)
        dialog.exec()

    def _system_info_text(self):
        return (
            f"Python: {platform.python_version()}\n"
            f"Qt/PySide6: {QApplication.instance().applicationVersion() or 'PySide6'}\n"
            f"SQLite: {sqlite3.sqlite_version}\n"
            f"Betriebssystem: {platform.system()} {platform.release()}\n"
            f"Projektordner: {self.base_dir}"
        )

    def _run_health_check(self, as_rows=False):
        rows = []

        def add(ok, name, detail):
            rows.append({"ok": bool(ok), "name": name, "detail": str(detail)})

        add(self.repository is not None, "SQLite / Repository", "bereit" if self.repository is not None else "nicht bereit")

        db_path = self.base_dir / "config" / "mediahub.sqlite3"
        add(db_path.exists(), "Datenbankdatei", db_path if db_path.exists() else f"nicht gefunden: {db_path}")

        for tool_name in ("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe", "deno.exe"):
            local_tool = self.base_dir / "tools" / tool_name
            system_tool = shutil.which(tool_name)
            if local_tool.exists():
                add(True, tool_name, f"lokal gefunden: {local_tool}")
            elif system_tool:
                add(True, tool_name, f"im Systempfad gefunden: {system_tool}")
            else:
                add(False, tool_name, "fehlt; bitte im Tool-Center installieren/prüfen")

        for folder_name in ("downloads", "downloads/work", "downloads/Fertig", "config", "logs", "tools", "docs"):
            folder = self.base_dir / folder_name
            try:
                folder.mkdir(parents=True, exist_ok=True)
                test_file = folder / ".write_test"
                test_file.write_text("ok", encoding="utf-8")
                test_file.unlink(missing_ok=True)
                add(True, f"Ordner {folder_name}", f"Schreibzugriff OK: {folder}")
            except Exception as exc:
                add(False, f"Ordner {folder_name}", f"kein Schreibzugriff: {exc}")

        add(self.scheduler_manager is not None, "Scheduler", "geladen" if self.scheduler_manager is not None else "nicht geladen")
        add(self.job_queue_manager is not None, "Job-Queue", "geladen" if self.job_queue_manager is not None else "nicht geladen")

        manual = self.base_dir / "docs" / "MediaHub_Anleitung.pdf"
        add(manual.exists(), "Anleitung", manual if manual.exists() else "PDF-Anleitung fehlt")

        if as_rows:
            return rows

        lines = []
        for row in rows:
            prefix = "✓" if row["ok"] else "⚠"
            lines.append(f"{prefix} {row['name']}: {row['detail']}")
        return lines

    def update_status(self, text):
        channel_count = len(self.controller.get_channels())
        self.status.showMessage(f"{text} | {channel_count} Kanäle geladen")