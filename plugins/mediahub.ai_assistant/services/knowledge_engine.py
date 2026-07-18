from __future__ import annotations

import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Iterable


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


class KnowledgeEngine:
    """Schnelle CRUD- und Suchschicht für knowledge.sqlite3."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=10.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA journal_mode = WAL")
        db.execute("PRAGMA synchronous = NORMAL")
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def ensure_schema(self) -> None:
        with self._connect() as db:
            columns = {
                row[1]
                for row in db.execute("PRAGMA table_info(media_items)").fetchall()
            }
            if "normalized_title" not in columns:
                db.execute(
                    "ALTER TABLE media_items ADD COLUMN normalized_title TEXT"
                )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_items_normalized_title "
                "ON media_items(normalized_title)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_aliases_item "
                "ON aliases(media_item_id)"
            )
            db.commit()

    def add_media_item(
        self,
        *,
        media_type: str,
        title: str,
        original_title: str | None = None,
        release_year: int | None = None,
        parent_id: int | None = None,
        season_number: int | None = None,
        episode_number: int | None = None,
        runtime_seconds: int | None = None,
        aliases: Iterable[str] = (),
    ) -> int:
        normalized = normalize_text(title)
        with self._connect() as db:
            existing = db.execute(
                """
                SELECT id FROM media_items
                WHERE normalized_title = ?
                  AND media_type = ?
                  AND COALESCE(release_year, -1) = COALESCE(?, -1)
                  AND COALESCE(season_number, -1) = COALESCE(?, -1)
                  AND COALESCE(episode_number, -1) = COALESCE(?, -1)
                LIMIT 1
                """,
                (
                    normalized,
                    media_type,
                    release_year,
                    season_number,
                    episode_number,
                ),
            ).fetchone()
            if existing:
                item_id = int(existing["id"])
                db.execute(
                    """
                    UPDATE media_items
                    SET canonical_title = ?,
                        original_title = COALESCE(?, original_title),
                        parent_id = COALESCE(?, parent_id),
                        runtime_seconds = COALESCE(?, runtime_seconds),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (title, original_title, parent_id, runtime_seconds, item_id),
                )
            else:
                cur = db.execute(
                    """
                    INSERT INTO media_items(
                        media_type, canonical_title, normalized_title,
                        original_title, release_year, parent_id,
                        season_number, episode_number, runtime_seconds
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        media_type,
                        title,
                        normalized,
                        original_title,
                        release_year,
                        parent_id,
                        season_number,
                        episode_number,
                        runtime_seconds,
                    ),
                )
                item_id = int(cur.lastrowid)

            for alias in aliases:
                alias = alias.strip()
                if not alias:
                    continue
                normalized_alias = normalize_text(alias)
                exists = db.execute(
                    """
                    SELECT 1 FROM aliases
                    WHERE media_item_id = ? AND normalized_alias = ?
                    LIMIT 1
                    """,
                    (item_id, normalized_alias),
                ).fetchone()
                if not exists:
                    db.execute(
                        """
                        INSERT INTO aliases(
                            media_item_id, alias, language, normalized_alias
                        )
                        VALUES(?, ?, NULL, ?)
                        """,
                        (item_id, alias, normalized_alias),
                    )
            db.commit()
            return item_id

    def add_relation(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        *,
        sort_order: int | None = None,
        note: str | None = None,
    ) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO relations(
                    source_id, target_id, relation_type, sort_order, note
                )
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relation_type)
                DO UPDATE SET
                    sort_order = excluded.sort_order,
                    note = excluded.note
                """,
                (source_id, target_id, relation_type, sort_order, note),
            )
            db.commit()

    def search(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        normalized = normalize_text(query)
        like = f"%{normalized}%"

        with self._connect() as db:
            rows = db.execute(
                """
                SELECT DISTINCT
                    m.id,
                    m.media_type,
                    m.canonical_title,
                    m.original_title,
                    m.release_year,
                    m.parent_id,
                    m.season_number,
                    m.episode_number,
                    m.runtime_seconds,
                    CASE
                        WHEN m.normalized_title = ? THEN 0
                        WHEN a.normalized_alias = ? THEN 1
                        WHEN m.normalized_title LIKE ? THEN 2
                        ELSE 3
                    END AS rank
                FROM media_items m
                LEFT JOIN aliases a ON a.media_item_id = m.id
                WHERE m.normalized_title LIKE ?
                   OR a.normalized_alias LIKE ?
                ORDER BY rank, m.canonical_title COLLATE NOCASE
                LIMIT ?
                """,
                (normalized, normalized, like, like, like, int(limit)),
            ).fetchall()

            results: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["aliases"] = [
                    alias_row["alias"]
                    for alias_row in db.execute(
                        "SELECT alias FROM aliases "
                        "WHERE media_item_id = ? ORDER BY alias COLLATE NOCASE",
                        (row["id"],),
                    ).fetchall()
                ]
                item["relations"] = [
                    dict(rel)
                    for rel in db.execute(
                        """
                        SELECT
                            r.relation_type,
                            r.sort_order,
                            r.note,
                            t.id AS target_id,
                            t.canonical_title AS target_title,
                            t.media_type AS target_type,
                            t.release_year AS target_year
                        FROM relations r
                        JOIN media_items t ON t.id = r.target_id
                        WHERE r.source_id = ?
                        ORDER BY
                            COALESCE(r.sort_order, 999999),
                            t.canonical_title COLLATE NOCASE
                        """,
                        (row["id"],),
                    ).fetchall()
                ]
                results.append(item)
            return results


    def all_items(self, limit: int = 5000) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT
                    id,
                    media_type,
                    canonical_title,
                    original_title,
                    release_year,
                    parent_id,
                    season_number,
                    episode_number,
                    runtime_seconds
                FROM media_items
                ORDER BY canonical_title COLLATE NOCASE
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

            results: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["aliases"] = [
                    alias_row["alias"]
                    for alias_row in db.execute(
                        "SELECT alias FROM aliases "
                        "WHERE media_item_id = ? ORDER BY alias COLLATE NOCASE",
                        (row["id"],),
                    ).fetchall()
                ]
                item["relations"] = [
                    dict(rel)
                    for rel in db.execute(
                        """
                        SELECT
                            r.relation_type,
                            r.sort_order,
                            r.note,
                            t.id AS target_id,
                            t.canonical_title AS target_title,
                            t.media_type AS target_type,
                            t.release_year AS target_year
                        FROM relations r
                        JOIN media_items t ON t.id = r.target_id
                        WHERE r.source_id = ?
                        ORDER BY
                            COALESCE(r.sort_order, 999999),
                            t.canonical_title COLLATE NOCASE
                        """,
                        (row["id"],),
                    ).fetchall()
                ]
                results.append(item)
            return results

    def stats(self) -> dict[str, Any]:
        with self._connect() as db:
            return {
                "media_items": db.execute(
                    "SELECT COUNT(*) FROM media_items"
                ).fetchone()[0],
                "aliases": db.execute(
                    "SELECT COUNT(*) FROM aliases"
                ).fetchone()[0],
                "relations": db.execute(
                    "SELECT COUNT(*) FROM relations"
                ).fetchone()[0],
                "editions": db.execute(
                    "SELECT COUNT(*) FROM editions"
                ).fetchone()[0],
            }

    def seed_demo_data(self) -> dict[str, int]:
        """Kleine lokale Testdaten, bewusst ohne externen Download."""
        series_id = self.add_media_item(
            media_type="series",
            title="12 Monkeys",
            release_year=2015,
            aliases=("Twelve Monkeys",),
        )
        season_id = self.add_media_item(
            media_type="season",
            title="12 Monkeys – Staffel 1",
            parent_id=series_id,
            season_number=1,
        )
        episode_id = self.add_media_item(
            media_type="episode",
            title="Splinter",
            parent_id=season_id,
            season_number=1,
            episode_number=1,
            runtime_seconds=2586,
            aliases=("Der Zeitreisende",),
        )
        self.add_relation(
            series_id,
            season_id,
            "contains",
            sort_order=1,
        )
        self.add_relation(
            season_id,
            episode_id,
            "contains",
            sort_order=1,
        )
        return {
            "series_id": series_id,
            "season_id": season_id,
            "episode_id": episode_id,
        }
