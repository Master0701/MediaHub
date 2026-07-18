from __future__ import annotations

import sqlite3
from pathlib import Path


class MediaHubDatabaseReader:
    """Öffnet mediahub.sqlite3 ausdrücklich schreibgeschützt."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def status(self) -> dict:
        if not self.path.exists():
            return {
                "path": str(self.path),
                "exists": False,
                "read_only": True,
                "tables": [],
                "message": "mediahub.sqlite3 wurde noch nicht gefunden.",
            }

        uri = self.path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=5.0) as db:
            tables = [
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
        return {
            "path": str(self.path),
            "exists": True,
            "read_only": True,
            "tables": tables,
            "table_count": len(tables),
            "message": "MediaHub-Datenbank wurde schreibgeschützt geöffnet.",
        }
