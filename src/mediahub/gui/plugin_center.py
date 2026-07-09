from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.mediahub.gui.ui_standards import (
    PANEL_MARGIN,
    PANEL_SPACING,
    configure_button,
    make_title,
)
from src.mediahub.plugins.plugin_loader import PluginLoader


class PluginCenter(QWidget):
    def __init__(self, base_dir: Path, parent=None):
        super().__init__(parent)

        self.base_dir = Path(base_dir)
        self.loader = PluginLoader(self.base_dir)
        self.open_plugin_callback = None
        self.plugins = []

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)
        layout.setSpacing(PANEL_SPACING)

        layout.addWidget(make_title("🔌 Plugin Center"))

        info = QLabel(
            "MediaHub v1.0 erkennt Plugins über plugin.json-Dateien. "
            "Plugins werden sicher angezeigt, aber noch nicht automatisch ausgeführt. "
            "Die vollständige Plugin-Ausführung folgt mit MediaHub 2.0."
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

        self.btn_refresh = configure_button(
            QPushButton("Plugins neu laden"),
            "Pluginliste neu einlesen.",
        )
        self.btn_install = configure_button(
            QPushButton(".mhplugin installieren"),
            "Ein Plugin aus einer .mhplugin-Datei installieren.",
        )
        self.btn_open = configure_button(
            QPushButton("Plugin anzeigen"),
            "Ausgewähltes Plugin anzeigen.",
        )
        self.btn_folder = configure_button(
            QPushButton("Plugin-Ordner öffnen"),
            "Ordner für lokale Plugins öffnen.",
        )

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_install.clicked.connect(self.install_plugin)
        self.btn_open.clicked.connect(self.open_selected_plugin)
        self.btn_folder.clicked.connect(self.open_plugins_folder)

        buttons.addWidget(self.btn_refresh)
        buttons.addWidget(self.btn_install)
        buttons.addWidget(self.btn_open)
        buttons.addWidget(self.btn_folder)
        buttons.addStretch(1)

        layout.addLayout(buttons)

        self.status = QLabel("Bereit")
        layout.addWidget(self.status)

    def refresh(self):
        self.plugins = self.loader.discover()

        self.plugin_list.clear()

        for plugin in self.plugins:
            prefix = "✓" if plugin.enabled else "○"
            item = QListWidgetItem(f"{prefix} {plugin.name} ({plugin.version})")
            item.setData(256, plugin.plugin_id)
            self.plugin_list.addItem(item)

        if self.plugins:
            self.plugin_list.setCurrentRow(0)
        else:
            self.details.setPlainText(
                "Keine Plugins gefunden.\n\n"
                "Plugins können später so hinzugefügt werden:\n\n"
                "1. Plugin-Ordner nach plugins/<plugin_name> kopieren\n"
                "2. oder eine .mhplugin-Datei installieren\n\n"
                "Jedes Plugin braucht mindestens eine plugin.json."
            )

        self.status.setText(f"{len(self.plugins)} Plugin(s) gefunden")

    def show_details(self, row):
        if row < 0 or row >= len(self.plugins):
            return

        plugin = self.plugins[row]

        self.details.setPlainText(
            f"Name: {plugin.name}\n"
            f"ID: {plugin.plugin_id}\n"
            f"Version: {plugin.version}\n"
            f"Autor: {plugin.author}\n"
            f"Typ: {plugin.plugin_type}\n"
            f"Aktiv: {'Ja' if plugin.enabled else 'Nein'}\n"
            f"Sicherer Modus: {'Ja' if plugin.safe_mode else 'Nein'}\n"
            f"Entry: {plugin.entry or '-'}\n"
            f"Icon: {plugin.icon or '-'}\n"
            f"Pfad: {plugin.path}\n\n"
            f"Beschreibung:\n{plugin.description}\n\n"
            "Hinweis:\n"
            "MediaHub v1.0 zeigt Plugins nur an und installiert .mhplugin-Dateien. "
            "Die echte Plugin-Ausführung kommt mit MediaHub 2.0."
        )

    def selected_plugin_id(self):
        row = self.plugin_list.currentRow()

        if row < 0 or row >= len(self.plugins):
            return None

        return self.plugins[row].plugin_id

    def open_selected_plugin(self):
        plugin_id = self.selected_plugin_id()

        if not plugin_id:
            QMessageBox.information(self, "Plugin", "Kein Plugin ausgewählt.")
            return

        if self.open_plugin_callback:
            self.open_plugin_callback(plugin_id)
            return

        QMessageBox.information(
            self,
            "Plugin",
            "Dieses Plugin wurde erkannt, wird in MediaHub v1.0 aber noch nicht ausgeführt.\n\n"
            f"Plugin-ID: {plugin_id}",
        )

    def install_plugin(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Plugin installieren",
            str(Path.home()),
            "MediaHub Plugins (*.mhplugin)",
        )

        if not file_path:
            return

        ok, message = self.loader.install_mhplugin(Path(file_path))

        if ok:
            QMessageBox.information(self, "Plugin installiert", message)
        else:
            QMessageBox.warning(self, "Plugin-Fehler", message)

        self.refresh()

    def open_plugins_folder(self):
        folder = self.base_dir / "plugins"
        folder.mkdir(parents=True, exist_ok=True)

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))