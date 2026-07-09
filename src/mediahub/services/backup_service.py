import json
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path


class BackupService:
    """Erstellt und verwaltet MediaHub-Backups.

    Das Backup ist bewusst normales ZIP + manifest.json, damit es auch ohne
    MediaHub geprüft oder notfalls von Hand entpackt werden kann.
    """

    BACKUP_VERSION = 1

    def __init__(self, base_dir: Path, app_version: str = "unknown", logger=None):
        self.base_dir = Path(base_dir)
        self.app_version = app_version
        self.logger = logger
        self.backup_dir = self.base_dir / "Backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def list_backups(self) -> list[dict]:
        rows = []
        for path in sorted(self.backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
            manifest = self.read_manifest(path)
            rows.append({
                "path": path,
                "name": path.name,
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime),
                "manifest": manifest,
            })
        return rows

    def create_backup(
        self,
        name: str = "",
        comment: str = "",
        include_database: bool = True,
        include_config: bool = True,
        include_logs: bool = False,
        include_downloads: bool = False,
        progress_callback=None,
    ) -> dict:
        safe_name = self._safe_filename(name) if name else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if not safe_name.lower().endswith(".zip"):
            safe_name += ".zip"
        target = self.backup_dir / safe_name
        if target.exists():
            stem = target.stem
            suffix = target.suffix
            target = self.backup_dir / f"{stem}_{datetime.now().strftime('%H%M%S')}{suffix}"

        started = datetime.now()
        manifest = self._build_manifest(comment, include_database, include_config, include_logs, include_downloads)
        files = self._collect_files(include_database, include_config, include_logs, include_downloads)
        total = max(len(files), 1)

        def emit(message):
            if progress_callback:
                progress_callback(message)

        emit("Backup wird vorbereitet...")
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=4, ensure_ascii=False))
            archive.writestr("version.json", json.dumps({"mediahub_version": self.app_version}, indent=4, ensure_ascii=False))
            for index, file_path in enumerate(files, start=1):
                try:
                    arcname = file_path.relative_to(self.base_dir).as_posix()
                    archive.write(file_path, arcname)
                    emit(f"[{index}/{total}] {arcname}")
                except Exception as exc:
                    emit(f"Fehler bei {file_path}: {exc}")

        duration = (datetime.now() - started).total_seconds()
        result = {
            "ok": True,
            "path": target,
            "size": target.stat().st_size,
            "duration": duration,
            "manifest": manifest,
        }
        if self.logger:
            self.logger.info(f"Backup erstellt: {target}")
        return result

    def read_manifest(self, backup_path: Path) -> dict:
        backup_path = Path(backup_path)
        try:
            with zipfile.ZipFile(backup_path, "r") as archive:
                with archive.open("manifest.json") as handle:
                    return json.loads(handle.read().decode("utf-8"))
        except Exception:
            return {}

    def restore_backup(self, backup_path: Path, progress_callback=None) -> dict:
        """Einfache Wiederherstellung für config-Dateien.

        Downloads und Logs werden absichtlich nicht automatisch überschrieben.
        Für rc8 ist Restore damit sicher: Erst wird ein Sicherheitsbackup von
        config erzeugt, dann werden config-Dateien aus dem ZIP eingespielt.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            return {"ok": False, "message": "Backup-Datei nicht gefunden."}

        def emit(message):
            if progress_callback:
                progress_callback(message)

        safety_dir = self.backup_dir / f"before_restore_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        safety_dir.mkdir(parents=True, exist_ok=True)
        config_dir = self.base_dir / "config"
        if config_dir.exists():
            shutil.copytree(config_dir, safety_dir / "config", dirs_exist_ok=True)
            emit(f"Sicherheitskopie erstellt: {safety_dir}")

        restored = []
        with zipfile.ZipFile(backup_path, "r") as archive:
            for member in archive.namelist():
                if member.startswith("config/") and not member.endswith("/"):
                    archive.extract(member, self.base_dir)
                    restored.append(member)
                    emit(f"Wiederhergestellt: {member}")

        if self.logger:
            self.logger.info(f"Backup wiederhergestellt: {backup_path}")
        return {"ok": True, "message": f"{len(restored)} config-Datei(en) wiederhergestellt.", "safety_dir": safety_dir}

    def delete_backup(self, backup_path: Path) -> None:
        Path(backup_path).unlink(missing_ok=True)
        if self.logger:
            self.logger.info(f"Backup gelöscht: {backup_path}")

    def _collect_files(self, include_database, include_config, include_logs, include_downloads):
        files = []
        if include_database:
            db = self.base_dir / "config" / "mediahub.sqlite3"
            if db.exists():
                files.append(db)
        if include_config:
            config = self.base_dir / "config"
            if config.exists():
                for path in config.rglob("*"):
                    if path.is_file() and path.name != "mediahub.sqlite3":
                        files.append(path)
        if include_logs:
            logs = self.base_dir / "logs"
            if logs.exists():
                files.extend([p for p in logs.rglob("*") if p.is_file()])
        if include_downloads:
            downloads = self.base_dir / "downloads"
            if downloads.exists():
                files.extend([p for p in downloads.rglob("*") if p.is_file()])
        return sorted(set(files))

    def _build_manifest(self, comment, include_database, include_config, include_logs, include_downloads):
        stats = self._database_stats()
        return {
            "mediahub_version": self.app_version,
            "backup_version": self.BACKUP_VERSION,
            "created": datetime.now().isoformat(timespec="seconds"),
            "comment": comment,
            "includes": {
                "database": bool(include_database),
                "config": bool(include_config),
                "logs": bool(include_logs),
                "downloads": bool(include_downloads),
            },
            "channels": stats.get("channels", 0),
            "playlists": stats.get("playlists", 0),
            "videos": stats.get("videos", 0),
            "downloads": stats.get("downloads", 0),
        }

    def _database_stats(self):
        db = self.base_dir / "config" / "mediahub.sqlite3"
        if not db.exists():
            return {}
        stats = {}
        try:
            with sqlite3.connect(db) as con:
                for table, key in (("channels", "channels"), ("playlists", "playlists"), ("videos", "videos"), ("downloads", "downloads")):
                    try:
                        row = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                        stats[key] = int(row[0] if row else 0)
                    except sqlite3.Error:
                        stats[key] = 0
        except sqlite3.Error:
            return {}
        return stats

    def _safe_filename(self, value: str) -> str:
        value = value.strip().replace(" ", "_")
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        cleaned = "".join(ch for ch in value if ch in allowed)
        return cleaned or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
