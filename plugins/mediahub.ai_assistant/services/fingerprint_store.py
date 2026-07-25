from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class FingerprintReferenceStore:
    """Lokale Referenzzuordnung für reproduzierbare Video-Fingerprints."""

    def __init__(self, database_path: Path | None):
        self.database_path = Path(database_path) if database_path else None
        self.ensure_schema()

    def ensure_schema(self) -> None:
        if self.database_path is None:
            return
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_fingerprint_references (
                    fingerprint TEXT PRIMARY KEY,
                    media_type TEXT,
                    title TEXT NOT NULL,
                    year INTEGER,
                    season INTEGER,
                    episode INTEGER,
                    edition TEXT,
                    source_path TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_ai_fp_title ON ai_fingerprint_references(title)")

    def lookup(self, fingerprint: str | None) -> dict[str, Any] | None:
        if not fingerprint or self.database_path is None:
            return None
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM ai_fingerprint_references WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
        return dict(row) if row else None

    def register(self, fingerprint: str, identity: dict[str, Any], source_path: str | None = None) -> dict[str, Any]:
        if self.database_path is None:
            raise RuntimeError("Keine Wissensdatenbank verfügbar.")
        title = str(identity.get("title") or identity.get("title_candidate") or "").strip()
        if not fingerprint or not title:
            raise ValueError("Fingerprint und Titel werden benötigt.")
        episodes = identity.get("episodes") or []
        episode = identity.get("episode")
        if episode is None and episodes:
            episode = episodes[0]
        values = (
            fingerprint,
            identity.get("media_type"),
            title,
            identity.get("year"),
            identity.get("season"),
            episode,
            identity.get("edition") or identity.get("edition_candidate"),
            source_path,
        )
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """
                INSERT INTO ai_fingerprint_references
                (fingerprint, media_type, title, year, season, episode, edition, source_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    media_type=excluded.media_type,
                    title=excluded.title,
                    year=excluded.year,
                    season=excluded.season,
                    episode=excluded.episode,
                    edition=excluded.edition,
                    source_path=excluded.source_path,
                    updated_at=CURRENT_TIMESTAMP
                """,
                values,
            )
        return self.lookup(fingerprint) or {}

    def stats(self) -> dict[str, Any]:
        if self.database_path is None:
            return {"available": False, "references": 0}
        with sqlite3.connect(self.database_path) as db:
            count = db.execute("SELECT COUNT(*) FROM ai_fingerprint_references").fetchone()[0]
        return {"available": True, "references": int(count), "database": str(self.database_path)}
