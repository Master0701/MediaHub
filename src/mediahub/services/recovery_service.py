import os
import sqlite3
from datetime import datetime
from pathlib import Path


class RecoveryService:
    """Wartungsfunktionen für das Recovery Center.

    Alle Funktionen sind absichtlich defensiv gehalten: rc8 löscht keine Medien
    automatisch, sondern prüft, protokolliert und optimiert sicher.
    """

    MEDIA_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".opus", ".wav", ".flac"}

    def __init__(self, base_dir: Path, logger=None):
        self.base_dir = Path(base_dir)
        self.logger = logger
        self.db_path = self.base_dir / "config" / "mediahub.sqlite3"

    def run_database_check(self) -> dict:
        if not self.db_path.exists():
            return {"ok": False, "message": "Datenbank nicht gefunden.", "details": []}
        try:
            with sqlite3.connect(self.db_path) as con:
                rows = con.execute("PRAGMA integrity_check").fetchall()
            details = [str(row[0]) for row in rows]
            ok = details == ["ok"]
            return {"ok": ok, "message": "Datenbankprüfung OK." if ok else "Datenbankprüfung meldet Probleme.", "details": details}
        except sqlite3.Error as exc:
            return {"ok": False, "message": f"Datenbankprüfung fehlgeschlagen: {exc}", "details": []}

    def optimize_database(self) -> dict:
        if not self.db_path.exists():
            return {"ok": False, "message": "Datenbank nicht gefunden.", "details": []}
        before = self.db_path.stat().st_size
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute("PRAGMA optimize")
                con.execute("VACUUM")
            after = self.db_path.stat().st_size
            saved = max(0, before - after)
            return {
                "ok": True,
                "message": f"Datenbank optimiert. Ersparnis: {self._format_size(saved)}.",
                "details": [f"Vorher: {self._format_size(before)}", f"Nachher: {self._format_size(after)}"],
            }
        except sqlite3.Error as exc:
            return {"ok": False, "message": f"Optimierung fehlgeschlagen: {exc}", "details": []}

    def cleanup_database(self) -> dict:
        """Sichere Datenbankpflege ohne Datenverlust."""
        if not self.db_path.exists():
            return {"ok": False, "message": "Datenbank nicht gefunden.", "details": []}
        details = []
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute("PRAGMA foreign_keys = ON")
                con.execute("PRAGMA optimize")
                for table in ("jobs", "downloads", "videos", "playlists", "channels", "scheduled_tasks"):
                    try:
                        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        details.append(f"{table}: {count} Einträge")
                    except sqlite3.Error:
                        details.append(f"{table}: Tabelle nicht vorhanden")
                con.commit()
            return {"ok": True, "message": "Datenbank bereinigt/geprüft.", "details": details}
        except sqlite3.Error as exc:
            return {"ok": False, "message": f"Datenbankpflege fehlgeschlagen: {exc}", "details": details}

    def find_orphan_downloads(self, limit: int = 200) -> dict:
        downloads_dir = self.base_dir / "downloads"
        if not downloads_dir.exists():
            return {"ok": True, "message": "Downloadordner nicht vorhanden.", "details": []}

        known_paths = set()
        if self.db_path.exists():
            try:
                with sqlite3.connect(self.db_path) as con:
                    for table in ("downloads", "videos"):
                        cols = self._columns(con, table)
                        for col in ("file_path", "path", "filename", "local_path"):
                            if col in cols:
                                try:
                                    rows = con.execute(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''").fetchall()
                                    for row in rows:
                                        p = Path(str(row[0]))
                                        known_paths.add(str(p).lower())
                                        known_paths.add(str((self.base_dir / p)).lower())
                                except sqlite3.Error:
                                    pass
            except sqlite3.Error:
                pass

        orphans = []
        total_files = 0
        total_size = 0
        for path in downloads_dir.rglob("*"):
            if not path.is_file():
                continue
            total_files += 1
            if path.suffix.lower() not in self.MEDIA_EXTENSIONS:
                continue
            total_size += path.stat().st_size
            full = str(path).lower()
            rel = str(path.relative_to(self.base_dir)).lower()
            if known_paths and full not in known_paths and rel not in known_paths:
                orphans.append(path)
            elif not known_paths:
                # Wenn die DB keine Pfadspalten kennt, nur zählen und nicht als Fehler werten.
                pass

        details = [str(p.relative_to(self.base_dir)) for p in orphans[:limit]]
        if not known_paths:
            return {
                "ok": True,
                "message": f"{total_files} Datei(en) im Downloadordner gefunden. Keine auswertbaren Dateipfade in der Datenbank.",
                "details": [f"Mediengröße gesamt: {self._format_size(total_size)}"],
            }
        return {
            "ok": True,
            "message": f"{len(orphans)} mögliche verwaiste Medien-Datei(en) gefunden.",
            "details": details or ["Keine verwaisten Medien gefunden."],
        }

    def check_archive(self) -> dict:
        downloads_dir = self.base_dir / "downloads"
        finished_dir = downloads_dir / "Fertig"
        work_dir = downloads_dir / "work"
        details = []
        for folder in (downloads_dir, finished_dir, work_dir):
            folder.mkdir(parents=True, exist_ok=True)
            files = [p for p in folder.rglob("*") if p.is_file()]
            size = sum(p.stat().st_size for p in files)
            details.append(f"{folder.relative_to(self.base_dir)}: {len(files)} Datei(en), {self._format_size(size)}")
        return {"ok": True, "message": "Archiv-/Downloadordner geprüft.", "details": details}

    def _columns(self, con, table):
        try:
            return {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
        except sqlite3.Error:
            return set()

    def _format_size(self, size):
        size = float(size or 0)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
