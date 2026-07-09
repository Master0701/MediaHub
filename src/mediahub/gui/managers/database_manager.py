class DatabaseManager:
    """Zentraler Zugriffspunkt für Datenbank-Status im GUI-Bereich."""

    def __init__(self, repository=None, log_panel=None):
        self.repository = repository
        self.log_panel = log_panel

    def write_startup_status(self):
        if self.repository is None or self.log_panel is None:
            return
        self.log_panel.write(
            f"Datenbank bereit: SQLite Schema {self.repository.get_schema_version()} | "
            f"{self.repository.get_channel_count()} Kanäle | "
            f"{self.repository.get_playlist_count()} Playlists"
        )
