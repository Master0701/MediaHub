from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class PluginInfo:
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: str
    enabled: bool
    path: Path
    entry: str = ""
    icon: str = ""
    safe_mode: bool = True
    class_name: str = ""
    minimum_mediahub_version: str = ""
    permissions: list[str] = field(default_factory=list)


class MediaHubPluginAPI:
    """Kleine, kontrollierte API für externe Plugins.

    In Fix 1 werden ausschließlich lesende Informationen freigegeben.
    Weitere Befehle werden später einzeln ergänzt und geprüft.
    """

    def __init__(
        self,
        *,
        base_dir: Path,
        app_version: str,
        repository: Any = None,
        controller: Any = None,
        logger: Any = None,
        status_provider: Callable[[], dict] | None = None,
    ):
        self.base_dir = Path(base_dir)
        self.app_version = str(app_version)
        self._repository = repository
        self._controller = controller
        self._logger = logger
        self._status_provider = status_provider

    def get_status(self) -> dict:
        result = {
            "application": "MediaHub",
            "version": self.app_version,
            "connected": True,
            "channels": self.get_channel_count(),
            "playlists": self.get_playlist_count(),
            "videos": self.get_video_count(),
        }
        if self._status_provider is not None:
            try:
                extra = self._status_provider() or {}
                if isinstance(extra, dict):
                    result.update(extra)
            except Exception as error:
                self.log(f"Plugin-Status konnte nicht gelesen werden: {error}", level="warning")
        return result

    def get_channel_count(self) -> int:
        if self._repository is not None and hasattr(self._repository, "get_channel_count"):
            return int(self._repository.get_channel_count())
        if self._controller is not None and hasattr(self._controller, "get_channels"):
            return len(self._controller.get_channels() or [])
        return 0

    def get_playlist_count(self) -> int:
        if self._repository is not None and hasattr(self._repository, "get_playlist_count"):
            return int(self._repository.get_playlist_count())
        return 0

    def get_video_count(self) -> int:
        repository = self._repository
        if repository is None:
            return 0
        if hasattr(repository, "get_video_count"):
            return int(repository.get_video_count())
        database = getattr(repository, "database", None)
        if database is not None and hasattr(database, "fetch_one"):
            row = database.fetch_one("SELECT COUNT(*) AS count FROM videos")
            return int(row["count"]) if row else 0
        return 0

    def log(self, message: str, *, level: str = "info") -> None:
        if self._logger is None:
            return
        method = getattr(self._logger, level, None) or getattr(self._logger, "info", None)
        if callable(method):
            method(f"[Plugin] {message}")
