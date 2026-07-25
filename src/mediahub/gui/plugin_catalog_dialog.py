from __future__ import annotations

import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.mediahub.services.ai_node_service import AINodeService
from src.mediahub.services.plugin_catalog_service import (
    CatalogPlugin,
    PluginCatalogService,
)
from src.mediahub.services.settings_service import SettingsService


class PluginCatalogDialog(QDialog):
    """Plugin-Store für MediaHub-Plugins und AI-Node-Plugins."""

    def __init__(self, plugin_loader, parent=None):
        super().__init__(parent)
        self.plugin_loader = plugin_loader
        self.service = PluginCatalogService()
        self.base_dir = self._resolve_base_dir()
        self.settings_service = SettingsService(self.base_dir)

        self.plugins: list[CatalogPlugin] = []
        self.ai_plugins: list[dict] = []

        self.setWindowTitle("MediaHub Plugin-Store")
        self.resize(840, 600)

        self.tabs = QTabWidget()
        self.mediahub_tab = QWidget()
        self.ai_tab = QWidget()

        self.tabs.addTab(self.mediahub_tab, "MediaHub-Plugins")
        self.tabs.addTab(self.ai_tab, "AI-Plugins")

        self._build_mediahub_tab()
        self._build_ai_tab()

        self.close_button = QPushButton("Schließen")
        self.close_button.clicked.connect(self.accept)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(bottom)

        self.tabs.currentChanged.connect(self._tab_changed)

        self.load_catalog()
        self.load_ai_plugins()

    def _build_mediahub_tab(self):
        self.list_widget = QListWidget()
        self.description = QTextEdit()
        self.description.setReadOnly(True)

        self.install_button = QPushButton(
            "Herunterladen und installieren"
        )
        self.project_button = QPushButton("GitHub-Seite öffnen")
        self.refresh_button = QPushButton("Katalog aktualisieren")

        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)
        buttons.addWidget(self.project_button)
        buttons.addWidget(self.install_button)

        layout = QVBoxLayout(self.mediahub_tab)
        layout.addWidget(QLabel("Verfügbare MediaHub-Plugins"))
        layout.addWidget(self.list_widget, 2)
        layout.addWidget(self.description, 1)
        layout.addLayout(buttons)

        self.refresh_button.clicked.connect(self.load_catalog)
        self.list_widget.currentRowChanged.connect(
            self.show_selected
        )
        self.install_button.clicked.connect(
            self.install_selected
        )
        self.project_button.clicked.connect(
            self.open_project_page
        )

    def _build_ai_tab(self):
        self.ai_status = QLabel("AI-Node wird geprüft ...")
        self.ai_status.setWordWrap(True)

        self.ai_list_widget = QListWidget()
        self.ai_description = QTextEdit()
        self.ai_description.setReadOnly(True)

        self.ai_refresh_button = QPushButton(
            "AI-Plugins neu laden"
        )
        self.ai_settings_hint = QLabel(
            "AI-Plugins werden auf dem Raspberry-Pi-AI-Node "
            "installiert und verwaltet."
        )
        self.ai_settings_hint.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.addWidget(self.ai_refresh_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self.ai_tab)
        layout.addWidget(self.ai_status)
        layout.addWidget(self.ai_settings_hint)
        layout.addWidget(self.ai_list_widget, 2)
        layout.addWidget(self.ai_description, 1)
        layout.addLayout(buttons)

        self.ai_refresh_button.clicked.connect(
            self.load_ai_plugins
        )
        self.ai_list_widget.currentRowChanged.connect(
            self.show_selected_ai_plugin
        )

    def _resolve_base_dir(self) -> Path:
        candidates = (
            getattr(self.plugin_loader, "base_dir", None),
            getattr(self.plugin_loader, "app_dir", None),
            getattr(self.plugin_loader, "root_dir", None),
        )

        for candidate in candidates:
            if candidate:
                return Path(candidate)

        return Path.cwd()

    def _tab_changed(self, index: int):
        if self.tabs.widget(index) is self.ai_tab:
            self.load_ai_plugins()

    def load_catalog(self):
        try:
            self.plugins = self.service.fetch_catalog()
        except Exception as error:
            QMessageBox.warning(
                self,
                "Plugin-Katalog",
                f"Katalog konnte nicht geladen werden:\n{error}",
            )
            return

        self.list_widget.clear()

        for plugin in self.plugins:
            suffix = (
                " – manuelle Installation"
                if plugin.manual_only or not plugin.auto_install
                else ""
            )
            item = QListWidgetItem(
                f"{plugin.name}  v{plugin.version}{suffix}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                plugin.plugin_id,
            )
            self.list_widget.addItem(item)

        if self.plugins:
            self.list_widget.setCurrentRow(0)

    def selected_plugin(self):
        row = self.list_widget.currentRow()
        return (
            self.plugins[row]
            if 0 <= row < len(self.plugins)
            else None
        )

    def show_selected(self, _row):
        plugin = self.selected_plugin()

        if not plugin:
            self.description.clear()
            self.install_button.setEnabled(False)
            return

        note = (
            plugin.manual_install_message
            if plugin.manual_only
            else ""
        )

        self.description.setPlainText(
            f"{plugin.name}\n"
            f"Version: {plugin.version}\n\n"
            f"{plugin.description}"
            + (f"\n\n{note}" if note else "")
        )

        self.install_button.setEnabled(True)
        self.install_button.setText(
            "Manuelle Installation anzeigen"
            if plugin.manual_only or not plugin.auto_install
            else "Herunterladen und installieren"
        )

    def install_selected(self):
        plugin = self.selected_plugin()
        if not plugin:
            return

        if plugin.manual_only or not plugin.auto_install:
            self._show_manual_install_dialog(plugin)
            return

        try:
            package = self.service.download_plugin(plugin)
            ok, message = self.plugin_loader.install_mhplugin(
                package
            )
        except Exception as error:
            QMessageBox.warning(
                self,
                "Plugin installieren",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Plugin installieren",
            message,
        )

        if ok:
            self.accept()

    def _show_manual_install_dialog(
        self,
        plugin: CatalogPlugin,
    ):
        message = QMessageBox(self)
        message.setWindowTitle(
            f"{plugin.name} manuell installieren"
        )
        message.setIcon(
            QMessageBox.Icon.Information
        )
        message.setText(
            f"{plugin.name} kann nicht automatisch "
            "über den Plugin-Store installiert werden."
        )
        message.setInformativeText(
            (
                plugin.manual_install_message
                or (
                    "Bitte lade die aktuelle .mhplugin-Datei "
                    "manuell von der offiziellen GitHub-Seite "
                    "herunter und installiere sie anschließend "
                    "über die MediaHub-Plugin-Verwaltung."
                )
            )
        )

        github_button = message.addButton(
            "GitHub-Seite öffnen",
            QMessageBox.ButtonRole.ActionRole,
        )
        message.addButton(
            "Schließen",
            QMessageBox.ButtonRole.RejectRole,
        )
        message.exec()

        if message.clickedButton() is github_button:
            webbrowser.open(plugin.project_page)

    def open_project_page(self):
        plugin = self.selected_plugin()
        if plugin:
            webbrowser.open(plugin.project_page)

    def load_ai_plugins(self):
        settings = self.settings_service.load()
        service = AINodeService.from_settings(
            settings,
            timeout=5.0,
        )
        health = service.health()

        self.ai_list_widget.clear()
        self.ai_plugins = []

        if not health.online:
            self.ai_status.setText(
                "AI-Node offline oder nicht eingerichtet: "
                f"{health.message}"
            )
            self.ai_description.setPlainText(
                "Richte den Raspberry-Pi-AI-Node zuerst unter "
                "Globale Einstellungen → KI-Verbindungen ein."
            )
            return

        self.ai_status.setText(
            f"AI-Node online – Status: {health.status}, "
            f"Version: {health.version}"
        )

        try:
            self.ai_plugins = service.list_plugins()
        except Exception as error:
            self.ai_description.setPlainText(
                "Die AI-Plugin-Liste konnte nicht geladen werden:\n"
                f"{error}"
            )
            return

        for plugin in self.ai_plugins:
            plugin_id = str(
                plugin.get("id")
                or plugin.get("plugin_id")
                or "unbekannt"
            )
            name = str(plugin.get("name") or plugin_id)
            version = str(plugin.get("version") or "unbekannt")
            enabled = bool(plugin.get("enabled", False))
            loaded = bool(plugin.get("loaded", False))

            state = []
            state.append(
                "aktiviert" if enabled else "deaktiviert"
            )
            state.append(
                "geladen" if loaded else "nicht geladen"
            )

            item = QListWidgetItem(
                f"{name}  v{version} – {', '.join(state)}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                plugin_id,
            )
            self.ai_list_widget.addItem(item)

        if self.ai_plugins:
            self.ai_list_widget.setCurrentRow(0)
        else:
            self.ai_description.setPlainText(
                "Der AI-Node ist online, aber es sind noch "
                "keine AI-Plugins installiert."
            )

    def show_selected_ai_plugin(self, row: int):
        if not 0 <= row < len(self.ai_plugins):
            self.ai_description.clear()
            return

        plugin = self.ai_plugins[row]
        plugin_id = str(
            plugin.get("id")
            or plugin.get("plugin_id")
            or "unbekannt"
        )
        name = str(plugin.get("name") or plugin_id)
        version = str(plugin.get("version") or "unbekannt")
        plugin_type = str(
            plugin.get("type")
            or plugin.get("plugin_type")
            or "unbekannt"
        )
        enabled = bool(plugin.get("enabled", False))
        loaded = bool(plugin.get("loaded", False))
        error = plugin.get("error")

        lines = [
            name,
            f"Plugin-ID: {plugin_id}",
            f"Version: {version}",
            f"Typ: {plugin_type}",
            f"Aktiviert: {'Ja' if enabled else 'Nein'}",
            f"Geladen: {'Ja' if loaded else 'Nein'}",
        ]

        if error:
            lines.extend(
                ["", f"Fehler: {error}"]
            )

        self.ai_description.setPlainText(
            "\n".join(lines)
        )
