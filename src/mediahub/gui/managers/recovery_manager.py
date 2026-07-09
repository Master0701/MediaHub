import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from src.mediahub.services.backup_service import BackupService
from src.mediahub.services.recovery_service import RecoveryService
from src.mediahub.services.release_service import ReleaseService


class RecoveryManager:
    def __init__(
        self,
        base_dir: Path,
        app_version: str,
        recovery_center=None,
        log_panel=None,
        update_status_callback=None,
        logger=None,
        repository=None,
    ):
        self.base_dir = Path(base_dir)
        self.repository = repository
        self.backup_service = BackupService(self.base_dir, app_version=app_version, logger=logger)
        self.recovery_service = RecoveryService(self.base_dir, logger=logger)
        self.release_service = ReleaseService(self.base_dir, app_version=app_version, logger=logger)
        self.recovery_center = recovery_center
        self.log_panel = log_panel
        self.update_status_callback = update_status_callback

        if self.recovery_center is not None:
            self.recovery_center.set_manager(self)
            self.refresh()

    def refresh(self):
        if self.recovery_center is not None:
            self.recovery_center.load_backups(self.backup_service.list_backups())

    def create_backup(self, name, comment, include_database=True, include_config=True, include_logs=False, include_downloads=False):
        def progress(message):
            self._log(message)
            if self.recovery_center is not None:
                self.recovery_center.append_output(message)

        result = self.backup_service.create_backup(
            name=name,
            comment=comment,
            include_database=include_database,
            include_config=include_config,
            include_logs=include_logs,
            include_downloads=include_downloads,
            progress_callback=progress,
        )
        self.refresh()
        self._status("Backup erstellt")
        return result

    def restore_backup(self, path):
        def progress(message):
            self._log(message)
            if self.recovery_center is not None:
                self.recovery_center.append_output(message)

        result = self.backup_service.restore_backup(path, progress_callback=progress)
        self.refresh()
        self._status("Backup wiederhergestellt" if result.get("ok") else "Wiederherstellung fehlgeschlagen")
        return result

    def delete_backup(self, path):
        self.backup_service.delete_backup(path)
        self.refresh()
        self._status("Backup gelöscht")

    def open_backup_folder(self):
        self.backup_service.backup_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.backup_service.backup_dir)))

    def create_auto_backup_task(self, interval_hours=24):
        if self.repository is None:
            return None
        interval_hours = int(interval_hours or 24)
        name_map = {24: "Tägliches Auto-Backup", 168: "Wöchentliches Auto-Backup", 720: "Monatliches Auto-Backup"}
        task_id = self.repository.create_scheduled_task(
            name=name_map.get(interval_hours, f"Auto-Backup alle {interval_hours} Stunden"),
            task_type="backup",
            channel_name="",
            interval_hours=interval_hours,
            payload={
                "name_prefix": "AutoBackup",
                "include_database": True,
                "include_config": True,
                "include_logs": False,
                "include_downloads": False,
            },
            enabled=True,
            next_run_at="",
        )
        self._log(f"Auto-Backup-Aufgabe angelegt: alle {interval_hours} Stunde(n).")
        self._status("Auto-Backup geplant")
        if self.recovery_center is not None:
            self.recovery_center.append_output("Auto-Backup-Aufgabe wurde im Scheduler angelegt.")
        return task_id

    def run_database_check(self):
        return self._run_maintenance(self.recovery_service.run_database_check)

    def optimize_database(self):
        return self._run_maintenance(self.recovery_service.optimize_database)

    def cleanup_database(self):
        return self._run_maintenance(self.recovery_service.cleanup_database)

    def find_orphan_downloads(self):
        return self._run_maintenance(self.recovery_service.find_orphan_downloads)

    def check_archive(self):
        return self._run_maintenance(self.recovery_service.check_archive)

    def _run_maintenance(self, func):
        result = func()
        message = result.get("message", "Fertig")
        self._log(message)
        if self.recovery_center is not None:
            self.recovery_center.append_output(message)
            for detail in result.get("details", []):
                self.recovery_center.append_output(f"  {detail}")
        self._status(message)
        return result


    def run_selftest(self, mode="quick"):
        mode = mode if mode in ("quick", "full", "release") else "quick"
        script = self.base_dir / "tools" / "mediahub_selftest.py"
        if not script.exists():
            return {"ok": False, "message": "Selbsttest-Script wurde nicht gefunden.", "error": str(script), "output": ""}
        try:
            process = subprocess.run(
                [sys.executable, str(script), "--mode", mode],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=180 if mode == "release" else 90,
            )
            output = (process.stdout or "") + (process.stderr or "")
            ok = process.returncode == 0
            message = "Selbsttest erfolgreich abgeschlossen." if ok else "Selbsttest hat Fehler gefunden."
            self._log(message)
            self._status(message)
            return {"ok": ok, "message": message, "output": output, "error": "" if ok else output}
        except Exception as exc:
            return {"ok": False, "message": "Selbsttest konnte nicht gestartet werden.", "error": str(exc), "output": ""}

    def open_latest_selftest_report(self):
        html = self.base_dir / "logs" / "selftest_latest.html"
        text = self.base_dir / "logs" / "selftest_latest.txt"
        target = html if html.exists() else text
        if target.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            self._status("Selbsttest-Bericht geöffnet")
        else:
            self._status("Noch kein Selbsttest-Bericht vorhanden")


    def prepare_release(self):
        result = self.release_service.prepare_release(include_sample_channel=False)
        message = "Release-Vorbereitung abgeschlossen." if result.get("ok") else "Release-Vorbereitung mit Fehlern beendet."
        self._log(message)
        if self.recovery_center is not None:
            self.recovery_center.append_output(message)
            self.recovery_center.append_output(f"Ziel: {result.get('target')}")
            for warning in result.get("warnings", []):
                self.recovery_center.append_output(f"WARN: {warning}")
            for detail in result.get("details", []):
                self.recovery_center.append_output(f"OK: {detail}")
        self._status(message)
        return {"ok": result.get("ok", False), "message": message, "details": result.get("details", []), "warnings": result.get("warnings", []), "target": result.get("target")}

    def build_release_package(self):
        result = self.release_service.build_release_package()
        message = "Release-Paket erstellt." if result.get("ok") else "Release-Paket mit Fehlern beendet."
        self._log(message)
        if self.recovery_center is not None:
            self.recovery_center.append_output(message)
            self.recovery_center.append_output(f"Ziel: {result.get('target')}")
            if result.get("zip"):
                self.recovery_center.append_output(f"ZIP: {result.get('zip')}")
            for warning in result.get("warnings", []):
                self.recovery_center.append_output(f"WARN: {warning}")
            for detail in result.get("details", []):
                self.recovery_center.append_output(f"OK: {detail}")
        self._status(message)
        return {
            "ok": result.get("ok", False),
            "message": message,
            "details": result.get("details", []),
            "warnings": result.get("warnings", []),
            "target": result.get("target"),
            "zip": result.get("zip"),
        }

    def create_build_files(self):
        result = self.release_service.create_build_files()
        if self.recovery_center is not None:
            self.recovery_center.append_output(result.get("message", "Build-Dateien erstellt."))
            self.recovery_center.append_output(f"Ziel: {result.get('target')}")
        self._status(result.get("message", "Build-Dateien erstellt."))
        return result

    def clean_runtime_preview(self):
        result = self.release_service.clean_runtime_preview()
        if self.recovery_center is not None:
            self.recovery_center.append_output(result.get("message", ""))
            for detail in result.get("details", []):
                self.recovery_center.append_output(f"  {detail}")
        self._status(result.get("message", "Bereinigungs-Trockenlauf abgeschlossen."))
        return result

    def open_latest_release_report(self):
        target = self.release_service.latest_report()
        if target.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            self._status("Release-Bericht geöffnet")
        else:
            self._status("Noch kein Release-Bericht vorhanden")

    def _log(self, message):
        if self.log_panel is not None:
            self.log_panel.write(message)

    def _status(self, message):
        if self.update_status_callback:
            self.update_status_callback(message)
