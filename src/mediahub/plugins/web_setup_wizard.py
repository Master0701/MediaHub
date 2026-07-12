from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Any

from src.mediahub.models.channel import Channel
from src.mediahub.services.profile_service import ProfileService


class WebSetupWizardService:
    """Webfähige Leselogik des MediaHub-Start-Assistenten.

    Speichern und Starten erfolgen weiterhin kontrolliert im Qt-Hauptthread
    über die zentrale Plugin-Action-Registry.
    """

    def __init__(self, *, base_dir: Path, youtube_service=None, playlist_service=None):
        self.base_dir = Path(base_dir)
        self.youtube_service = youtube_service
        self.playlist_service = playlist_service

    @staticmethod
    def guess_channel_name(url: str) -> str:
        parsed = urlparse((url or "").strip())
        parts = [part for part in unquote(parsed.path or "").strip("/").split("/") if part]
        if not parts:
            return "Neuer Kanal"
        candidate = parts[-1]
        if candidate.lower() in {"videos", "playlists", "featured", "streams", "shorts"} and len(parts) >= 2:
            candidate = parts[-2]
        if candidate.startswith("@"):
            candidate = candidate[1:]
        if candidate.lower() in {"channel", "c", "user"}:
            return "Neuer Kanal"
        candidate = re.sub(r"[-_]+", " ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        return candidate.title() if candidate else "Neuer Kanal"

    @staticmethod
    def _safe_name(value: str) -> str:
        text = re.sub(r'[<>:"/\\|?*]+', "_", str(value or "")).strip()
        return re.sub(r"\s+", " ", text) or "Neuer Kanal"

    def get_options(self) -> dict:
        return {
            "profiles": ProfileService.names(),
            "profile_defaults": {name: dict(ProfileService.get(name)) for name in ProfileService.names()},
            "filename_templates": [
                "{title} S{season:02}E{episode:02}",
                "S{season:02}E{episode:02} {title}",
                "{title} (S{season:02}E{episode:02})",
                "{title} - S{season:02}E{episode:02}",
                "{series} - {title} S{season:02}E{episode:02}",
                "{series} - S{season:02}E{episode:02} - {title}",
            ],
            "containers": ["MKV", "MP4", "WebM"],
            "resolutions": ["Beste", "4K", "1440p", "1080p", "720p", "480p"],
            "audio_formats": ["M4A", "MP3", "AAC", "FLAC", "OGG", "WAV"],
            "playlist_folder_modes": ["Nur Staffeln", "Playlist-Ordner", "Keine Unterordner"],
            "defaults": {
                "profile": "Plex", "filename_template": "{title} S{season:02}E{episode:02}",
                "container": "MKV", "resolution": "1080p", "audio_format": "M4A",
                "audio_only": False, "create_nfo": True, "create_poster": True,
                "create_fanart": True, "clean_work_folder": True,
                "playlist_folder_mode": "Nur Staffeln", "create_job": True,
                "create_scheduler": False, "interval_hours": 24,
                "start_sync_now": False, "start_download_after_sync": False,
            },
        }

    def analyze_source(self, payload: dict) -> dict:
        url = str(payload.get("url") or "").strip()
        if not url:
            raise ValueError("Bitte eine YouTube-URL eingeben.")
        if "youtube.com" not in url and "youtu.be" not in url:
            raise ValueError("Die URL sieht nicht wie eine YouTube-URL aus.")
        info = {}
        if self.youtube_service is not None:
            info = self.youtube_service.get_channel_info(url) or {}
        name = str(info.get("name") or info.get("title") or "").strip() or self.guess_channel_name(url)
        safe = self._safe_name(name)
        return {
            "url": url,
            "name": name,
            "channel_id": str(info.get("id") or info.get("channel_id") or info.get("uploader_id") or ""),
            "description": str(info.get("description") or info.get("channel_description") or info.get("about") or ""),
            "youtube_name": str(info.get("name") or info.get("title") or name),
            "channel_url": str(info.get("webpage_url") or info.get("channel_url") or url),
            "avatar": str(info.get("avatar") or ""),
            "banner": str(info.get("banner") or ""),
            "work_folder": str(Path("downloads") / "work" / safe),
            "target_folder": str(Path("downloads") / "Fertig" / safe),
        }

    def load_playlists(self, payload: dict) -> list[dict]:
        url = str(payload.get("url") or "").strip()
        name = str(payload.get("name") or "").strip() or self.guess_channel_name(url)
        if not url:
            raise ValueError("Bitte zuerst eine YouTube-URL eingeben.")
        if self.playlist_service is None:
            raise RuntimeError("Playlist-Service ist nicht verfügbar.")
        temp_channel = Channel(name=name, url=url)
        loaded = self.playlist_service.load_playlists(temp_channel) or []
        synced = self.playlist_service.sync_playlist_settings(temp_channel, loaded) or []
        result = []
        for index, item in enumerate(synced, start=1):
            data = dict(item or {})
            result.append({
                "playlist_id": str(data.get("playlist_id") or index),
                "title": str(data.get("title") or data.get("name") or f"Playlist {index}"),
                "display_name": str(data.get("display_name") or data.get("plex_name") or data.get("title") or data.get("name") or f"Playlist {index}"),
                "url": str(data.get("url") or ""),
                "enabled": bool(data.get("enabled", data.get("selected", True))),
                "season": int(data.get("season") or index),
                "video_count": int(data.get("video_count") or 0),
                "thumbnail_url": str(data.get("thumbnail_url") or ""),
            })
        return result
