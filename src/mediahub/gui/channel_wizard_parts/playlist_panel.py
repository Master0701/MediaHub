from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel

from src.mediahub.gui.widgets.playlist_table import PlaylistTable


class ChannelWizardPlaylistPanel(QGroupBox):
    def __init__(self):
        super().__init__("Gefundene Playlists")

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Noch keine Playlists geladen.")
        self.playlist_table = PlaylistTable()

        layout.addWidget(self.info_label)
        layout.addWidget(self.playlist_table)

    def set_playlists(self, playlists):
        if not playlists:
            self.info_label.setText("Keine Playlists gefunden.")
            self.playlist_table.set_playlists([])
            return

        self.info_label.setText(
            f"{len(playlists)} Playlists gefunden. "
            "Import, Plex-Name und Staffel können hier angepasst werden."
        )
        self.playlist_table.set_playlists(playlists)

    def get_selected_playlists(self):
        return self.playlist_table.get_selected_playlists()

    def get_playlist_settings(self):
        return self.playlist_table.get_playlist_settings()