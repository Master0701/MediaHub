from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from src.mediahub.gui.ui_standards import PANEL_MARGIN, PANEL_SPACING, configure_button, make_title
from src.mediahub.plugins.plugin_api import MediaHubPluginAPI
from src.mediahub.plugins.plugin_loader import PluginLoader
from src.mediahub.plugins.plugin_runtime import PluginRuntime
from src.mediahub.gui.plugin_settings_dialog import WebPluginSettingsDialog


class PluginCenter(QWidget):
    def __init__(self, base_dir: Path, parent=None, *, mediahub_api: MediaHubPluginAPI | None = None):
        super().__init__(parent)
        self.base_dir = Path(base_dir)
        self.loader = PluginLoader(self.base_dir)
        self.runtime = PluginRuntime(mediahub_api) if mediahub_api is not None else None
        self.plugins = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)
        layout.setSpacing(PANEL_SPACING)
        layout.addWidget(make_title("🔌 Plugin Center"))

        info = QLabel(
            "MediaHub erkennt installierte .mhplugin-Pakete und kann freigegebene Plugins "
            "kontrolliert starten und stoppen. Plugin 1 nutzt zunächst nur eine lesende API."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        self.plugin_list = QListWidget()
        self.plugin_list.setMinimumWidth(260)
        self.plugin_list.currentRowChanged.connect(self.show_details)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumWidth(420)
        splitter.addWidget(self.plugin_list)
        splitter.addWidget(self.details)
        splitter.setSizes([320, 680])
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_refresh = configure_button(QPushButton("Plugins neu laden"), "Pluginliste neu einlesen.")
        self.btn_install = configure_button(QPushButton(".mhplugin installieren"), "Plugin-Paket installieren.")
        self.btn_start = configure_button(QPushButton("Plugin starten"), "Ausgewähltes Plugin starten.")
        self.btn_stop = configure_button(QPushButton("Plugin stoppen"), "Ausgewähltes Plugin stoppen.")
        self.btn_open = configure_button(QPushButton("Weboberfläche öffnen"), "Lokale Plugin-Webseite öffnen.")
        self.btn_settings = configure_button(QPushButton("Plugin-Einstellungen"), "Einstellungen des ausgewählten Plugins öffnen.")
        self.btn_remove = configure_button(QPushButton("Plugin entfernen"), "Ausgewähltes Plugin deinstallieren.")
        self.btn_folder = configure_button(QPushButton("Plugin-Ordner öffnen"), "Lokalen Plugin-Ordner öffnen.")

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_install.clicked.connect(self.install_plugin)
        self.btn_start.clicked.connect(self.start_selected_plugin)
        self.btn_stop.clicked.connect(self.stop_selected_plugin)
        self.btn_open.clicked.connect(self.open_selected_plugin)
        self.btn_settings.clicked.connect(self.open_selected_plugin_settings)
        self.btn_remove.clicked.connect(self.remove_selected_plugin)
        self.btn_folder.clicked.connect(self.open_plugins_folder)

        for button in (self.btn_refresh, self.btn_install, self.btn_start, self.btn_stop,
                       self.btn_open, self.btn_settings, self.btn_remove, self.btn_folder):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.status = QLabel("Bereit")
        layout.addWidget(self.status)

    def refresh(self):
        selected = self.selected_plugin_id()
        self.plugins = self.loader.discover()
        self.plugin_list.clear()
        selected_row = 0
        for row, plugin in enumerate(self.plugins):
            running = self.runtime is not None and self.runtime.is_running(plugin.plugin_id)
            prefix = "▶" if running else ("✓" if plugin.enabled else "○")
            item = QListWidgetItem(f"{prefix} {plugin.name} ({plugin.version})")
            item.setData(256, plugin.plugin_id)
            self.plugin_list.addItem(item)
            if plugin.plugin_id == selected:
                selected_row = row
        if self.plugins:
            self.plugin_list.setCurrentRow(selected_row)
        else:
            self.details.setPlainText("Keine Plugins gefunden.\n\nInstalliere eine .mhplugin-Datei.")
        self.status.setText(f"{len(self.plugins)} Plugin(s) gefunden")

    def selected_plugin(self):
        row = self.plugin_list.currentRow()
        return self.plugins[row] if 0 <= row < len(self.plugins) else None

    def selected_plugin_id(self):
        plugin = self.selected_plugin()
        return plugin.plugin_id if plugin else None

    def show_details(self, row):
        if not (0 <= row < len(self.plugins)):
            return
        plugin = self.plugins[row]
        running = self.runtime is not None and self.runtime.is_running(plugin.plugin_id)
        permissions = ", ".join(plugin.permissions) if plugin.permissions else "keine"
        self.details.setPlainText(
            f"Name: {plugin.name}\nID: {plugin.plugin_id}\nVersion: {plugin.version}\n"
            f"Autor: {plugin.author}\nTyp: {plugin.plugin_type}\nAktiv: {'Ja' if plugin.enabled else 'Nein'}\n"
            f"Läuft: {'Ja' if running else 'Nein'}\nSicherer Modus: {'Ja' if plugin.safe_mode else 'Nein'}\n"
            f"Entry: {plugin.entry or '-'}\nKlasse: {plugin.class_name or 'automatisch'}\n"
            f"Min. MediaHub: {plugin.minimum_mediahub_version or '-'}\nRechte: {permissions}\n"
            f"Pfad: {plugin.path}\n\nBeschreibung:\n{plugin.description}"
        )

    def start_selected_plugin(self):
        plugin = self.selected_plugin()
        if plugin is None or self.runtime is None:
            QMessageBox.information(self, "Plugin", "Kein ausführbares Plugin ausgewählt.")
            return
        ok, message = self.runtime.start(plugin)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Plugin", message)
        self.refresh()

    def stop_selected_plugin(self):
        plugin = self.selected_plugin()
        if plugin is None or self.runtime is None:
            return
        ok, message = self.runtime.stop(plugin.plugin_id)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Plugin", message)
        self.refresh()

    def open_selected_plugin(self):
        plugin = self.selected_plugin()
        if plugin is None:
            QMessageBox.information(self, "Plugin", "Kein Plugin ausgewählt.")
            return
        if plugin.plugin_type == "web" and self.runtime and self.runtime.is_running(plugin.plugin_id):
            instance = self.runtime.get_instance(plugin.plugin_id)
            info = instance.get_plugin_settings() if instance and hasattr(instance, "get_plugin_settings") else {}
            QDesktopServices.openUrl(QUrl(str(info.get("active_url") or "http://127.0.0.1:8765/")))
            return
        QMessageBox.information(self, "Plugin", "Bitte das Web-Plugin zuerst starten.")

    def open_selected_plugin_settings(self):
        plugin = self.selected_plugin()
        if plugin is None or self.runtime is None:
            QMessageBox.information(self, "Plugin", "Kein Plugin ausgewählt.")
            return
        instance = self.runtime.get_instance(plugin.plugin_id)
        if instance is None:
            QMessageBox.information(self, "Plugin", "Bitte das Plugin zuerst starten.")
            return
        if not hasattr(instance, "get_plugin_settings") or not hasattr(instance, "update_plugin_settings"):
            QMessageBox.information(self, "Plugin", "Dieses Plugin besitzt keine eigenen Einstellungen.")
            return
        dialog = WebPluginSettingsDialog(instance, self)
        dialog.exec()
        self.show_details(self.plugin_list.currentRow())

    def install_plugin(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Plugin installieren", str(Path.home()), "MediaHub Plugins (*.mhplugin)")
        if not file_path:
            return
        ok, message = self.loader.install_mhplugin(Path(file_path))
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Plugin", message)
        self.refresh()

    def remove_selected_plugin(self):
        plugin = self.selected_plugin()
        if plugin is None:
            return
        if self.runtime and self.runtime.is_running(plugin.plugin_id):
            QMessageBox.warning(self, "Plugin", "Bitte das Plugin vor dem Entfernen stoppen.")
            return
        answer = QMessageBox.question(self, "Plugin entfernen", f"{plugin.name} wirklich entfernen?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        ok, message = self.loader.uninstall(plugin)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Plugin", message)
        self.refresh()

    def open_plugins_folder(self):
        folder = self.base_dir / "plugins"
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def shutdown_plugins(self):
        if self.runtime is not None:
            self.runtime.stop_all()
