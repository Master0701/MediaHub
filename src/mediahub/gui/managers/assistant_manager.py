from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from src.mediahub.services.settings_service import SettingsService


@dataclass
class AssistantCheck:
    area: str
    title: str
    status: str
    message: str
    points: int
    max_points: int
    action: str = ""

    @property
    def icon(self) -> str:
        if self.status == "ok":
            return "🟢"
        if self.status == "warn":
            return "🟡"
        return "🔴"

    def as_dict(self) -> dict:
        return {
            "area": self.area,
            "title": self.title,
            "status": self.status,
            "message": self.message,
            "points": self.points,
            "max_points": self.max_points,
            "action": self.action,
            "icon": self.icon,
        }


class AssistantManager:
    """Sammelt die MediaHub-Pruefungen fuer RC9.2.

    Der Manager ist absichtlich defensiv: Wenn eine Pruefung nicht moeglich ist,
    wird MediaHub nicht blockiert, sondern der Assistent zeigt nur eine Warnung.
    """

    def __init__(
        self,
        base_dir: Path,
        tool_service=None,
        repository=None,
        scheduler_manager=None,
        recovery_manager=None,
        assistant_panel=None,
        dashboard_panel=None,
        log_panel=None,
        update_status_callback: Callable[[str], None] | None = None,
    ):
        self.base_dir = Path(base_dir)
        self.tool_service = tool_service
        self.repository = repository
        self.scheduler_manager = scheduler_manager
        self.recovery_manager = recovery_manager
        self.assistant_panel = assistant_panel
        self.dashboard_panel = dashboard_panel
        self.log_panel = log_panel
        self.update_status_callback = update_status_callback
        self.settings_service = SettingsService(self.base_dir)

        if self.assistant_panel is not None:
            self.assistant_panel.set_manager(self)

    def refresh(self) -> dict:
        report = self.build_report()
        if self.assistant_panel is not None:
            self.assistant_panel.load_report(report)
        if self.dashboard_panel is not None and hasattr(self.dashboard_panel, "set_assistant_report"):
            self.dashboard_panel.set_assistant_report(report)
        if self.update_status_callback:
            self.update_status_callback(f"Assistent: Health Score {report['score']} %")
        return report

    def create_backup(self):
        if self.recovery_manager is None:
            return None
        result = self.recovery_manager.create_backup(
            name="Assistent_Backup",
            comment="Automatisch vom MediaHub Assistenten erstellt.",
            include_database=True,
            include_config=True,
            include_logs=False,
            include_downloads=False,
        )
        self._log("Assistent: Backup erstellt.")
        self.refresh()
        return result

    def optimize_database(self):
        if self.recovery_manager is None:
            return None
        result = self.recovery_manager.optimize_database()
        self._log("Assistent: Datenbankoptimierung ausgefuehrt.")
        self.refresh()
        return result

    def open_recovery_center(self):
        window = getattr(self.recovery_manager, "recovery_center", None)
        return window

    def build_report(self) -> dict:
        checks: list[AssistantCheck] = []
        checks.extend(self._check_tools())
        checks.append(self._check_database())
        checks.append(self._check_download_folder())
        checks.append(self._check_write_permissions())
        checks.append(self._check_backup_age())
        checks.append(self._check_scheduler())
        checks.append(self._check_free_space())

        max_points = sum(c.max_points for c in checks) or 1
        points = sum(c.points for c in checks)
        score = int(round((points / max_points) * 100))

        if score >= 90:
            level = "ok"
            headline = "MediaHub ist in gutem Zustand."
        elif score >= 70:
            level = "warn"
            headline = "MediaHub hat ein paar Empfehlungen."
        else:
            level = "error"
            headline = "MediaHub braucht Aufmerksamkeit."

        sorted_checks = sorted(checks, key=lambda c: {"error": 0, "warn": 1, "ok": 2}.get(c.status, 3))
        return {
            "score": score,
            "level": level,
            "headline": headline,
            "checks": [c.as_dict() for c in sorted_checks],
            "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }

    def _check_tools(self) -> Iterable[AssistantCheck]:
        if self.tool_service is None:
            yield AssistantCheck("System", "Tools", "warn", "ToolService nicht verfuegbar.", 0, 20)
            return
        tools = self.tool_service.check_tools()
        important = ["yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe"]
        points_each = 7
        for name in important:
            exists = bool(tools.get(name))
            yield AssistantCheck(
                "System",
                name,
                "ok" if exists else "error",
                "vorhanden" if exists else "fehlt im tools-Ordner",
                points_each if exists else 0,
                points_each,
                "Tool-Center öffnen" if not exists else "",
            )

    def _check_database(self) -> AssistantCheck:
        db_path = self.base_dir / "config" / "mediahub.sqlite3"
        if not db_path.exists():
            return AssistantCheck("Datenbank", "SQLite", "error", "Datenbank fehlt.", 0, 20, "Recovery Center öffnen")
        try:
            with sqlite3.connect(db_path) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            size_mb = db_path.stat().st_size / (1024 * 1024)
            if str(result).lower() != "ok":
                return AssistantCheck("Datenbank", "SQLite", "error", f"Integritaetscheck: {result}", 0, 20, "Datenbank prüfen")
            if size_mb > 500:
                return AssistantCheck("Datenbank", "SQLite", "warn", f"OK, aber groß: {size_mb:.1f} MB", 12, 20, "Optimieren")
            return AssistantCheck("Datenbank", "SQLite", "ok", f"OK ({size_mb:.1f} MB)", 20, 20)
        except Exception as error:
            return AssistantCheck("Datenbank", "SQLite", "error", f"Fehler: {error}", 0, 20, "Datenbank prüfen")

    def _check_download_folder(self) -> AssistantCheck:
        folder = self.base_dir / "downloads"
        if not folder.exists():
            return AssistantCheck("Downloads", "Downloadordner", "warn", "Ordner fehlt und sollte angelegt werden.", 3, 10)
        return AssistantCheck("Downloads", "Downloadordner", "ok", str(folder), 10, 10)

    def _check_write_permissions(self) -> AssistantCheck:
        target = self.base_dir / "config" / ".write_test"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")
            target.unlink(missing_ok=True)
            return AssistantCheck("System", "Schreibrechte", "ok", "config/ ist beschreibbar.", 10, 10)
        except Exception as error:
            return AssistantCheck("System", "Schreibrechte", "error", f"Keine Schreibrechte: {error}", 0, 10)

    def _check_backup_age(self) -> AssistantCheck:
        backup_dir = self.base_dir / "Backups"
        backups = list(backup_dir.glob("*.zip")) if backup_dir.exists() else []
        if not backups:
            return AssistantCheck("Backups", "Letztes Backup", "warn", "Noch kein Backup gefunden.", 0, 20, "Backup erstellen")
        newest = max(backups, key=lambda p: p.stat().st_mtime)
        age_days = int((datetime.now().timestamp() - newest.stat().st_mtime) // 86400)
        if age_days > 14:
            return AssistantCheck("Backups", "Letztes Backup", "warn", f"vor {age_days} Tagen", 8, 20, "Backup erstellen")
        return AssistantCheck("Backups", "Letztes Backup", "ok", f"vor {age_days} Tagen", 20, 20)

    def _check_scheduler(self) -> AssistantCheck:
        try:
            if self.repository is None:
                return AssistantCheck("Scheduler", "Scheduler", "warn", "Keine Datenbank fuer Schedulerstatus.", 3, 10)
            rows = self.repository.database.fetch_all("SELECT COUNT(*) AS count FROM scheduled_tasks WHERE enabled = 1")
            count = int(dict(rows[0]).get("count") or 0) if rows else 0
            if count <= 0:
                return AssistantCheck("Scheduler", "Aktive Aufgaben", "warn", "Keine aktive Scheduler-Aufgabe.", 4, 10, "Scheduler öffnen")
            return AssistantCheck("Scheduler", "Aktive Aufgaben", "ok", f"{count} aktiv", 10, 10)
        except Exception:
            return AssistantCheck("Scheduler", "Aktive Aufgaben", "warn", "Schedulerstatus nicht verfuegbar.", 4, 10)

    def _check_free_space(self) -> AssistantCheck:
        try:
            usage = shutil.disk_usage(self.base_dir)
            free_gb = usage.free / (1024 ** 3)
            if free_gb < 5:
                return AssistantCheck("System", "Freier Speicher", "error", f"nur {free_gb:.1f} GB frei", 0, 10)
            if free_gb < 20:
                return AssistantCheck("System", "Freier Speicher", "warn", f"{free_gb:.1f} GB frei", 5, 10)
            return AssistantCheck("System", "Freier Speicher", "ok", f"{free_gb:.1f} GB frei", 10, 10)
        except Exception as error:
            return AssistantCheck("System", "Freier Speicher", "warn", f"nicht pruefbar: {error}", 5, 10)

    def _log(self, message: str) -> None:
        if self.log_panel is not None:
            self.log_panel.write(message)
