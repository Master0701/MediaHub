import json
from pathlib import Path
from typing import Any


class SettingsService:
    """Einfache globale Einstellungen fuer MediaHub.

    Die Kanaleinstellungen bleiben weiterhin beim jeweiligen Kanal.
    Diese Datei speichert nur programmweite Optionen wie Pfade,
    Standardprofile, Tool-Hinweise und Backup-Vorgaben.
    """

    FILE_NAME = "settings.json"

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / "config"
        self.settings_file = self.config_dir / self.FILE_NAME

    def defaults(self) -> dict[str, Any]:
        return {
            "paths": {
                "downloads_dir": str(self.base_dir / "downloads"),
                "finished_dir": str(self.base_dir / "downloads" / "Fertig"),
                "work_dir": str(self.base_dir / "downloads" / "work"),
                "backup_dir": str(self.base_dir / "Backups"),
                "logs_dir": str(self.base_dir / "logs"),
                "tools_dir": str(self.base_dir / "tools"),
            },
            "download": {
                "default_profile": "Plex",
                "default_container": "MKV",
                "default_resolution": "1080p",
                "default_audio_format": "M4A",
                "audio_only": False,
                "clean_work_folder": True,
            },
            "plex": {
                "create_nfo": True,
                "create_poster": True,
                "create_fanart": True,
                "playlist_folder_mode": "Nur Staffeln",
            },
            "backup": {
                "automatic_enabled": False,
                "automatic_interval": "Wöchentlich",
                "keep_count": 10,
                "include_config": True,
                "include_database": True,
                "include_logs": False,
                "include_downloads": False,
            },
            "ui": {
                "start_page": "Dashboard",
                "confirm_before_restore": True,
            },
        }

    def load(self) -> dict[str, Any]:
        data = self.defaults()
        if not self.settings_file.exists():
            return data
        try:
            loaded = json.loads(self.settings_file.read_text(encoding="utf-8"))
            self._merge(data, loaded)
        except Exception:
            # Bei defekter settings.json startet MediaHub trotzdem mit Defaults.
            return data
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

    def reset(self) -> dict[str, Any]:
        data = self.defaults()
        self.save(data)
        return data

    def _merge(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._merge(target[key], value)
            else:
                target[key] = value
