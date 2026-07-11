from __future__ import annotations

import base64
import mimetypes
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
    """Kontrollierte Schnittstelle für externe MediaHub-Plugins."""
    def __init__(self, *, base_dir: Path, app_version: str, repository: Any = None, controller: Any = None, logger: Any = None, status_provider: Callable[[], dict] | None = None, download_status_provider: Callable[[], dict] | None = None):
        self.base_dir = Path(base_dir)
        self.app_version = str(app_version)
        self._repository = repository
        self._controller = controller
        self._logger = logger
        self._status_provider = status_provider
        self._download_status_provider = download_status_provider

    def get_status(self) -> dict:
        result = {"application":"MediaHub","version":self.app_version,"connected":True,"channels":self.get_channel_count(),"playlists":self.get_playlist_count(),"videos":self.get_video_count()}
        if self._status_provider is not None:
            try:
                extra=self._status_provider() or {}
                if isinstance(extra,dict): result.update(extra)
            except Exception as error: self.log(f"Plugin-Status konnte nicht gelesen werden: {error}",level="warning")
        return result

    def get_download_status(self) -> dict:
        """Liefert einen threadsicheren, rein lesenden Download-Schnappschuss."""
        default = {
            "active": False,
            "status": "Kein Download aktiv",
            "current_title": "",
            "item_progress": 0,
            "total_progress": 0,
            "done_count": 0,
            "total_count": 0,
            "queue": [],
        }
        if self._download_status_provider is None:
            return default
        try:
            value = self._download_status_provider() or {}
            if not isinstance(value, dict):
                return default
            result = dict(default)
            result.update(value)
            result["queue"] = list(result.get("queue") or [])
            return result
        except Exception as error:
            self.log(f"Downloadstatus konnte nicht gelesen werden: {error}", level="warning")
            return default

    def get_channels(self) -> list[dict]:
        """Liefert nur ausdrücklich freigegebene, lesende Kanaldaten."""
        raw=[]
        if self._controller is not None and hasattr(self._controller,"get_channels"):
            raw=list(self._controller.get_channels() or [])
        result=[]
        for index,channel in enumerate(raw):
            data=channel.to_dict() if hasattr(channel,"to_dict") else dict(channel) if isinstance(channel,dict) else {}
            name=str(data.get("name","") or "")
            playlists=list(data.get("playlist_settings") or [])
            video_count=sum(self._safe_int(p.get("video_count",0)) for p in playlists if isinstance(p,dict))
            if self._repository is not None:
                try:
                    repo_playlists=self._repository.get_playlists_for_channel(name) if hasattr(self._repository,"get_playlists_for_channel") else []
                    if repo_playlists:
                        playlists=repo_playlists
                        video_count=sum(self._safe_int(p.get("video_count",0)) for p in repo_playlists)
                except Exception as error:
                    self.log(f"Playlist-Zahlen für {name} konnten nicht gelesen werden: {error}",level="warning")
            result.append({
                "index":index,"name":name,"url":str(data.get("url","") or ""),"channel_id":str(data.get("channel_id","") or ""),
                "description":str(data.get("description","") or ""),"profile":str(data.get("profile","Plex") or "Plex"),
                "resolution":str(data.get("resolution","") or ""),"audio_only":bool(data.get("audio_only",False)),
                "playlist_count":len(playlists),"video_count":video_count,"poster_data_uri":self._image_data_uri(data.get("poster")),
            })
        return result

    def _image_data_uri(self,value: Any) -> str:
        if not value: return ""
        try:
            path=Path(str(value))
            if not path.is_absolute(): path=(self.base_dir/path).resolve()
            if not path.is_file() or path.stat().st_size>2*1024*1024: return ""
            mime=mimetypes.guess_type(path.name)[0] or "image/jpeg"
            return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        except Exception: return ""

    @staticmethod
    def _safe_int(value: Any) -> int:
        try: return int(value or 0)
        except (TypeError,ValueError): return 0

    def get_channel_count(self) -> int:
        if self._repository is not None and hasattr(self._repository,"get_channel_count"): return int(self._repository.get_channel_count())
        if self._controller is not None and hasattr(self._controller,"get_channels"): return len(self._controller.get_channels() or [])
        return 0
    def get_playlist_count(self) -> int:
        if self._repository is not None and hasattr(self._repository,"get_playlist_count"): return int(self._repository.get_playlist_count())
        return 0
    def get_video_count(self) -> int:
        repository=self._repository
        if repository is None: return 0
        if hasattr(repository,"get_video_count"): return int(repository.get_video_count())
        database=getattr(repository,"database",None)
        if database is not None and hasattr(database,"fetch_one"):
            row=database.fetch_one("SELECT COUNT(*) AS count FROM videos")
            return int(row["count"]) if row else 0
        return 0
    def log(self,message: str,*,level: str="info") -> None:
        if self._logger is None: return
        method=getattr(self._logger,level,None) or getattr(self._logger,"info",None)
        if callable(method): method(f"[Plugin] {message}")
