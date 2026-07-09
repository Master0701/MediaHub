from pathlib import Path
from typing import Optional

from src.mediahub.models.channel import Channel
from src.mediahub.storage.channel_store import ChannelStore


class ChannelController:
    def __init__(self, config_dir: Path, logger=None, repository=None):
        self.logger = logger
        self.repository = repository
        self.store = ChannelStore(config_dir)
        self.channels: list[Channel] = self.store.load()
        self.current_index: int = 0 if self.channels else -1

        # v0.7.0: JSON bleibt vorerst die aktive Quelle, SQLite wird aber
        # automatisch synchron gehalten. So können wir später gefahrlos auf
        # die Datenbank umstellen.
        self.sync_repository()

    def get_channels(self) -> list[Channel]:
        return self.channels

    def get_current_channel(self) -> Optional[Channel]:
        if 0 <= self.current_index < len(self.channels):
            return self.channels[self.current_index]
        return None

    def set_current_index(self, index: int) -> Optional[Channel]:
        self.current_index = index
        return self.get_current_channel()

    def sync_repository(self) -> None:
        if self.repository is None:
            return

        try:
            self.repository.sync_channels(self.channels)
        except Exception as error:
            if self.logger:
                self.logger.error(f"SQLite-Synchronisierung fehlgeschlagen: {error}")

    def save(self) -> None:
        self.store.save(self.channels)
        self.sync_repository()
        if self.logger:
            self.logger.info("Kanäle gespeichert")

    def update_current_channel(self, **changes) -> None:
        channel = self.get_current_channel()

        if channel is None:
            return

        for key, value in changes.items():
            if hasattr(channel, key):
                setattr(channel, key, value)

        self.save()

    def add_channel(self, channel: Channel) -> int:
        self.channels.append(channel)
        self.current_index = len(self.channels) - 1
        self.save()
        return self.current_index

    def update_channel(self, index: int, channel: Channel) -> None:
        if 0 <= index < len(self.channels):
            self.channels[index] = channel
            self.current_index = index
            self.save()

    def remove_channel(self, index: int) -> None:
        if 0 <= index < len(self.channels):
            channel_name = self.channels[index].name
            del self.channels[index]

            if self.channels:
                self.current_index = min(index, len(self.channels) - 1)
            else:
                self.current_index = -1

            self.save()

            if self.logger:
                self.logger.info(f"Kanal gelöscht: {channel_name}")
