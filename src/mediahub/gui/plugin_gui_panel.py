from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.mediahub.gui.ui_standards import PANEL_MARGIN, PANEL_SPACING, configure_button, make_title


class PluginGuiPanel(QWidget):
    """Host für native, Web- und spätere Dialog-Pluginoberflächen."""

    def __init__(self, plugin_id: str, plugin_center, parent=None):
        super().__init__(parent)
        self.plugin_id = str(plugin_id)
        self.plugin_center = plugin_center
        self._native_widget = None
        self._plugin_window = None
        self._window_widget = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)
        self.layout_root.setSpacing(PANEL_SPACING)

        self.title = make_title("Plugin-Oberfläche")
        self.layout_root.addWidget(self.title)

        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout_root.addWidget(self.description)

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.layout_root.addWidget(self.status)

        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(8)
        self.btn_open = configure_button(QPushButton("Oberfläche öffnen"), "Pluginoberfläche öffnen.")
        self.btn_start = configure_button(QPushButton("Plugin starten"), "Plugin starten.")
        self.btn_stop = configure_button(QPushButton("Plugin stoppen"), "Plugin stoppen.")
        self.btn_settings = configure_button(QPushButton("Plugin-Einstellungen"), "Plugin-Einstellungen öffnen.")
        self.btn_center = configure_button(QPushButton("Plugin Center"), "Zur bisherigen Plugin-Verwaltung wechseln.")

        self.btn_open.clicked.connect(self.open_gui)
        self.btn_start.clicked.connect(self.start_plugin)
        self.btn_stop.clicked.connect(self.stop_plugin)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_center.clicked.connect(self.plugin_center.open_in_navigation)

        for button in (self.btn_open, self.btn_start, self.btn_stop, self.btn_settings, self.btn_center):
            self.buttons.addWidget(button)
        self.buttons.addStretch(1)
        self.layout_root.addLayout(self.buttons)

        self.native_container = QWidget()
        self.native_layout = QVBoxLayout(self.native_container)
        self.native_layout.setContentsMargins(0, 0, 0, 0)
        self.native_layout.setSpacing(0)
        self.layout_root.addWidget(self.native_container, 1)

    def plugin(self):
        return self.plugin_center.get_plugin(self.plugin_id)

    def activate(self):
        plugin = self.plugin()
        if plugin is None:
            self.refresh()
            return
        if plugin.ui_type == "window":
            self._ensure_plugin_window()
            self.refresh()
            return
        elif plugin.ui_type == "native":
            self._ensure_native_widget()
        self.refresh()

    def refresh(self):
        plugin = self.plugin()
        if plugin is None:
            self.title.setText("Plugin-Oberfläche")
            self.description.setText("Das Plugin ist nicht mehr installiert.")
            self.status.setText("Status: nicht verfügbar")
            for button in (self.btn_open, self.btn_start, self.btn_stop, self.btn_settings):
                button.setEnabled(False)
            return

        running = self.plugin_center.is_running(plugin.plugin_id)
        ui_type = str(plugin.ui_type or "").strip().lower()
        is_native = ui_type == "native"
        is_window = ui_type == "window"
        self.title.setText(f"{plugin.ui_icon or '🧩'} {plugin.ui_title or plugin.name}")
        self.description.setText(plugin.description or "Dieses Plugin besitzt eine eigene Oberfläche.")
        self.status.setText(
            f"Version: {plugin.version}   |   Status: {'läuft' if running else 'gestoppt'}   |   "
            f"Darstellung: {'eigenes Desktop-Fenster' if is_window else ('direkt in MediaHub' if is_native else 'lokale Weboberfläche')}"
        )
        self.btn_open.setText(
            "In eigenem Fenster öffnen" if is_window
            else ("In MediaHub öffnen" if is_native else "Im Browser öffnen")
        )
        self.btn_open.setEnabled(plugin.enabled)
        self.btn_start.setVisible(not is_native and not is_window)
        self.btn_stop.setVisible(not is_native and not is_window)
        self.btn_start.setEnabled(plugin.enabled and not running)
        self.btn_stop.setEnabled(running)
        self.btn_settings.setEnabled(running and plugin.has_settings)
        self.native_container.setVisible(is_native)
        if is_native and self._native_widget is not None and hasattr(self._native_widget, "refresh"):
            try:
                self._native_widget.refresh()
            except Exception:
                pass


    def _ensure_plugin_window(self):
        plugin = self.plugin()
        if plugin is None:
            return False

        if self._plugin_window is not None:
            self._plugin_window.show()
            self._plugin_window.raise_()
            self._plugin_window.activateWindow()
            return True

        ok, message = self.plugin_center.start_plugin(self.plugin_id)
        if not ok:
            QMessageBox.warning(self, "Plugin-Oberfläche", message)
            return False

        instance = self.plugin_center.get_running_instance(self.plugin_id)
        factory = getattr(instance, "create_widget", None) if instance is not None else None
        if not callable(factory):
            QMessageBox.warning(
                self,
                "Plugin-Oberfläche",
                "Dieses Plugin ist als Desktop-Fenster eingetragen, stellt aber keine create_widget()-Methode bereit.",
            )
            return False

        try:
            window = QWidget(None, Qt.WindowType.Window)
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            window.setWindowTitle(plugin.ui_title or plugin.name)
            window.resize(1420, 860)
            window.setMinimumSize(1000, 650)
            layout = QVBoxLayout(window)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(0)
            widget = factory(parent=window)
            if widget is None:
                raise RuntimeError("Das Plugin hat kein Widget zurückgegeben.")
            layout.addWidget(widget, 1)
            self._plugin_window = window
            self._window_widget = widget

            def clear_window_reference(*_args):
                self._plugin_window = None
                self._window_widget = None

            window.destroyed.connect(clear_window_reference)
            window.show()
            window.raise_()
            window.activateWindow()
            return True
        except Exception as error:
            self._plugin_window = None
            self._window_widget = None
            QMessageBox.warning(self, "Plugin-Oberfläche", f"Plugin-Fenster konnte nicht geladen werden:\n{error}")
            return False

    def _ensure_native_widget(self):
        if self._native_widget is not None:
            return True
        ok, message = self.plugin_center.start_plugin(self.plugin_id)
        if not ok:
            QMessageBox.warning(self, "Plugin-Oberfläche", message)
            return False
        instance = self.plugin_center.get_running_instance(self.plugin_id)
        factory = getattr(instance, "create_widget", None) if instance is not None else None
        if not callable(factory):
            QMessageBox.warning(
                self,
                "Plugin-Oberfläche",
                "Dieses Plugin ist als native Oberfläche eingetragen, stellt aber keine create_widget()-Methode bereit.",
            )
            return False
        try:
            widget = factory(parent=self.native_container)
            if widget is None:
                raise RuntimeError("Das Plugin hat kein Widget zurückgegeben.")
            self._native_widget = widget
            self.native_layout.addWidget(widget, 1)
            return True
        except Exception as error:
            QMessageBox.warning(self, "Plugin-Oberfläche", f"Native Plugin-GUI konnte nicht geladen werden:\n{error}")
            return False

    def start_plugin(self):
        ok, message = self.plugin_center.start_plugin(self.plugin_id)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Plugin", message)
        self.refresh()

    def stop_plugin(self):
        ok, message = self.plugin_center.stop_plugin(self.plugin_id)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "Plugin", message)
        self.refresh()

    def open_gui(self):
        plugin = self.plugin()
        if plugin is None:
            return
        if plugin.ui_type == "window":
            self._ensure_plugin_window()
            self.refresh()
            return
        elif plugin.ui_type == "native":
            self._ensure_native_widget()
            self.refresh()
            return
        ok, message, url = self.plugin_center.ensure_plugin_gui(self.plugin_id)
        if not ok:
            QMessageBox.warning(self, "Plugin-Oberfläche", message)
            self.refresh()
            return
        if url:
            QDesktopServices.openUrl(QUrl(url))
        else:
            QMessageBox.information(self, "Plugin-Oberfläche", message)
        self.refresh()

    def open_settings(self):
        ok, message = self.plugin_center.open_plugin_settings(self.plugin_id)
        if not ok:
            QMessageBox.information(self, "Plugin", message)
        self.refresh()
