from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1


class KnowledgeDatabase:
    """Schnelle, versionierte SQLite-Wissensdatenbank."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA temp_store = MEMORY")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS media_items (
                    id INTEGER PRIMARY KEY,
                    media_type TEXT NOT NULL CHECK(media_type IN ('movie','series','season','episode','special','other')),
                    canonical_title TEXT NOT NULL,
                    original_title TEXT,
                    release_year INTEGER,
                    parent_id INTEGER REFERENCES media_items(id) ON DELETE CASCADE,
                    season_number INTEGER,
                    episode_number INTEGER,
                    runtime_seconds INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS aliases (
                    id INTEGER PRIMARY KEY,
                    media_item_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
                    alias TEXT NOT NULL,
                    language TEXT,
                    normalized_alias TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY,
                    source_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
                    target_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
                    relation_type TEXT NOT NULL,
                    sort_order INTEGER,
                    note TEXT,
                    UNIQUE(source_id, target_id, relation_type)
                );

                CREATE TABLE IF NOT EXISTS editions (
                    id INTEGER PRIMARY KEY,
                    media_item_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
                    edition_name TEXT NOT NULL,
                    runtime_seconds INTEGER,
                    edition_type TEXT,
                    notes TEXT,
                    UNIQUE(media_item_id, edition_name)
                );

                CREATE TABLE IF NOT EXISTS identification_cache (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    modified_ns INTEGER NOT NULL,
                    quick_hash TEXT,
                    media_item_id INTEGER REFERENCES media_items(id) ON DELETE SET NULL,
                    edition_id INTEGER REFERENCES editions(id) ON DELETE SET NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    method_summary TEXT,
                    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_path, file_size, modified_ns)
                );

                CREATE INDEX IF NOT EXISTS idx_media_items_title
                    ON media_items(canonical_title COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_media_items_type_year
                    ON media_items(media_type, release_year);
                CREATE INDEX IF NOT EXISTS idx_aliases_normalized
                    ON aliases(normalized_alias);
                CREATE INDEX IF NOT EXISTS idx_relations_source_type
                    ON relations(source_id, relation_type, sort_order);
                CREATE INDEX IF NOT EXISTS idx_relations_target_type
                    ON relations(target_id, relation_type);
                CREATE INDEX IF NOT EXISTS idx_editions_media
                    ON editions(media_item_id);
                CREATE INDEX IF NOT EXISTS idx_identification_quick_hash
                    ON identification_cache(quick_hash);
                """
            )
            db.execute(
                """
                INSERT INTO schema_info(key, value) VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    def health(self) -> dict:
        with self.connect() as db:
            version = db.execute(
                "SELECT value FROM schema_info WHERE key='schema_version'"
            ).fetchone()
            journal = db.execute("PRAGMA journal_mode").fetchone()[0]
            counts = {
                "media_items": db.execute("SELECT COUNT(*) FROM media_items").fetchone()[0],
                "relations": db.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
                "editions": db.execute("SELECT COUNT(*) FROM editions").fetchone()[0],
                "identification_cache": db.execute(
                    "SELECT COUNT(*) FROM identification_cache"
                ).fetchone()[0],
            }
        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "schema_version": int(version[0]) if version else 0,
            "journal_mode": str(journal),
            "counts": counts,
        }
