from pathlib import Path

from src.mediahub.models.channel import Channel
from src.mediahub.storage.json_store import JsonStore


class ChannelStore:
    CURRENT_VERSION = 3

    def __init__(self, config_dir: Path):
        self.store = JsonStore(Path(config_dir) / "channels.json")

    def load(self) -> list[Channel]:
        default_data = {
            "version": self.CURRENT_VERSION,
            "channels": []
        }

        data = self.store.load(default_data)
        data = self.migrate(data)

        channels = [
            Channel.from_dict(item)
            for item in data.get("channels", [])
        ]

        if data.get("version") != self.CURRENT_VERSION:
            self.save(channels)

        return channels

    def save(self, channels: list[Channel]) -> None:
        data = {
            "version": self.CURRENT_VERSION,
            "channels": [channel.to_dict() for channel in channels],
        }

        self.store.save(data)

    def migrate(self, data: dict) -> dict:
        version = data.get("version", 1)

        if version < 2:
            data = self.migrate_to_v2(data)
        if version < 3:
            data = self.migrate_to_v3(data)

        data["version"] = self.CURRENT_VERSION
        return data

    def migrate_to_v2(self, data: dict) -> dict:
        channels = data.get("channels", [])

        for channel in channels:
            channel.setdefault("playlist_folder_mode", "Nur Staffeln")
            channel.setdefault("playlist_settings", [])

        data["version"] = 2
        return data

    def migrate_to_v3(self, data: dict) -> dict:
        channels = data.get("channels", [])

        for channel in channels:
            channel.setdefault("channel_id", channel.get("id", ""))
            channel.setdefault("description", "")

        data["version"] = 3
        return data
