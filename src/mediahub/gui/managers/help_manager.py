class HelpManager:
    """Verbindet das Hilfe-Center mit Bereichen der MainWindow."""

    def __init__(self, main_window):
        self.main_window = main_window

    def callbacks(self) -> dict:
        return {
            "health": self.open_health,
            "recovery": self.open_recovery,
            "settings": self.open_settings,
            "tools": self.open_tools,
            "plugins": self.open_plugins,
            "downloads": self.open_downloads,
            "scheduler": self.open_scheduler,
            "channels": self.open_channels,
            "playlists": self.open_playlists,
        }

    def _switch_to_widget(self, attr_name: str):
        widget = getattr(self.main_window, attr_name, None)

        if widget is None:
            return

        if hasattr(self.main_window, "tabs"):
            index = self.main_window.tabs.indexOf(widget)

            if index >= 0:
                self.main_window.tabs.setCurrentIndex(index)

    def open_health(self):
        self._switch_to_widget("health_check_panel")

    def open_recovery(self):
        self._switch_to_widget("recovery_center")

    def open_settings(self):
        self._switch_to_widget("global_settings_panel")

    def open_tools(self):
        self._switch_to_widget("tool_center")

    def open_plugins(self):
        self._switch_to_widget("plugin_center")

    def open_downloads(self):
        self._switch_to_widget("download_queue_panel")

    def open_scheduler(self):
        self._switch_to_widget("scheduler_panel")

    def open_channels(self):
        self._switch_to_widget("channel_panel")

    def open_playlists(self):
        self._switch_to_widget("playlist_manager")