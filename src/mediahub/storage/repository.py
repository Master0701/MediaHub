from pathlib import Path
from typing import Iterable
import json
from datetime import datetime, timedelta

from src.mediahub.models.channel import Channel
from src.mediahub.storage.database import Database
from src.mediahub.storage.migration import MigrationManager


class MediaRepository:
    """Zentrale Datenebene für Kanäle, Playlists, Videos und Downloads."""

    def __init__(self, base_dir: Path, logger=None):
        self.base_dir = Path(base_dir)
        self.logger = logger
        self.database = Database(self.base_dir / "config" / "mediahub.sqlite3")
        self.migration_manager = MigrationManager(self.database)

    def initialize(self) -> None:
        self.migration_manager.migrate()
        self._ensure_performance_indexes()

    def _ensure_performance_indexes(self) -> None:
        """Legt fehlende SQLite-Indizes ohne Datenverlust an."""
        statements = (
            "CREATE INDEX IF NOT EXISTS idx_videos_status_flags ON videos(is_new, is_downloaded, is_members_only)",
            "CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_videos_upload_date ON videos(upload_date DESC)",
            "CREATE INDEX IF NOT EXISTS idx_videos_first_seen ON videos(first_seen_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_video_playlists_video ON video_playlists(video_db_id)",
            "CREATE INDEX IF NOT EXISTS idx_video_playlists_playlist ON video_playlists(playlist_id)",
            "CREATE INDEX IF NOT EXISTS idx_playlists_channel_id ON playlists(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_channels_name ON channels(name)",
        )
        with self.database.connect() as connection:
            for statement in statements:
                connection.execute(statement)
            connection.execute("PRAGMA optimize")
            connection.commit()

    def get_schema_version(self) -> str:
        row = self.database.fetch_one(
            "SELECT value FROM app_meta WHERE key = ?",
            ("schema_version",),
        )
        return row["value"] if row else "0"

    def get_channel_count(self) -> int:
        row = self.database.fetch_one("SELECT COUNT(*) AS count FROM channels")
        return int(row["count"]) if row else 0

    def get_playlist_count(self) -> int:
        row = self.database.fetch_one("SELECT COUNT(*) AS count FROM playlists")
        return int(row["count"]) if row else 0

    def sync_channels(self, channels: Iterable[Channel]) -> None:
        """Spiegelt die aktuelle JSON-Kanalverwaltung in SQLite.

        Ab v0.8.3 werden Kanäle und Playlists nicht mehr komplett gelöscht
        und neu angelegt. Das ist wichtig, weil Videos über channel_id und
        video_playlists dauerhaft mit diesen Datensätzen verbunden bleiben.
        """
        channel_list = list(channels)

        with self.database.connect() as connection:
            for channel in channel_list:
                channel_row = connection.execute(
                    "SELECT id FROM channels WHERE name = ? ORDER BY id LIMIT 1",
                    (channel.name,),
                ).fetchone()

                values = (
                    channel.name,
                    channel.url,
                    channel.profile,
                    int(bool(channel.audio_only)),
                    channel.filename_template,
                    channel.work_folder,
                    channel.target_folder,
                    channel.poster,
                    channel.fanart,
                    channel.container,
                    channel.resolution,
                    channel.audio_format,
                    int(bool(channel.create_nfo)),
                    int(bool(channel.create_poster)),
                    int(bool(channel.create_fanart)),
                    int(bool(channel.clean_work_folder)),
                    channel.playlist_folder_mode,
                )

                if channel_row:
                    channel_id = channel_row["id"]
                    connection.execute(
                        """
                        UPDATE channels
                        SET name = ?, url = ?, profile = ?, audio_only = ?,
                            filename_template = ?, work_folder = ?, target_folder = ?,
                            poster = ?, fanart = ?, container = ?, resolution = ?,
                            audio_format = ?, create_nfo = ?, create_poster = ?,
                            create_fanart = ?, clean_work_folder = ?,
                            playlist_folder_mode = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        values + (channel_id,),
                    )
                else:
                    cursor = connection.execute(
                        """
                        INSERT INTO channels (
                            name, url, profile, audio_only, filename_template,
                            work_folder, target_folder, poster, fanart, container,
                            resolution, audio_format, create_nfo, create_poster,
                            create_fanart, clean_work_folder, playlist_folder_mode,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        values,
                    )
                    channel_id = cursor.lastrowid

                self._upsert_playlists(connection, channel_id, channel.playlist_settings or [])

            connection.execute(
                """
                INSERT OR REPLACE INTO app_meta (key, value)
                VALUES ('last_channel_sync_count', ?)
                """,
                (str(len(channel_list)),),
            )
            connection.commit()

        if self.logger:
            self.logger.info(
                f"SQLite synchronisiert: {len(channel_list)} Kanäle, "
                f"{self.get_playlist_count()} Playlists"
            )

    def _upsert_playlists(self, connection, channel_id: int, playlist_settings: list[dict]) -> None:
        for index, playlist in enumerate(playlist_settings, start=1):
            playlist_id = playlist.get("playlist_id", "")
            title = playlist.get("playlist_name", playlist.get("title", ""))
            display_name = playlist.get("display_name", playlist.get("playlist_name", ""))
            url = playlist.get("url", "")
            season = int(playlist.get("season", index) or index)
            enabled = int(bool(playlist.get("enabled", True)))
            video_count = int(playlist.get("video_count", 0) or 0)
            new_video_count = int(playlist.get("new_video_count", 0) or 0)
            sort_order = int(playlist.get("sort_order", index) or index)

            row = connection.execute(
                """
                SELECT id, video_count, new_video_count
                FROM playlists
                WHERE channel_id = ?
                  AND (
                    (url != '' AND url = ?)
                    OR (playlist_id != '' AND playlist_id = ?)
                    OR title = ?
                    OR display_name = ?
                  )
                ORDER BY id
                LIMIT 1
                """,
                (channel_id, url, playlist_id, title, display_name),
            ).fetchone()

            if row:
                # Datenbank-Zähler nicht mit alten JSON-Werten überschreiben, wenn
                # durch Sync bereits bessere Werte vorhanden sind.
                merged_video_count = max(video_count, int(row["video_count"] or 0))
                merged_new_count = max(new_video_count, int(row["new_video_count"] or 0))
                connection.execute(
                    """
                    UPDATE playlists
                    SET playlist_id = ?, title = ?, display_name = ?, url = ?,
                        season = ?, enabled = ?, video_count = ?,
                        new_video_count = ?, sort_order = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        playlist_id, title, display_name, url, season, enabled,
                        merged_video_count, merged_new_count, sort_order, row["id"],
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO playlists (
                        channel_id, playlist_id, title, display_name, url, season,
                        enabled, video_count, new_video_count, sort_order, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        channel_id, playlist_id, title, display_name, url, season,
                        enabled, video_count, new_video_count, sort_order,
                    ),
                )

    def get_playlists_for_channel(self, channel_name: str) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT p.*
            FROM playlists p
            JOIN channels c ON c.id = p.channel_id
            WHERE c.name = ?
            ORDER BY p.sort_order, p.id
            """,
            (channel_name,),
        )
        return [dict(row) for row in rows]

    def get_active_playlists_for_channel(self, channel_name: str) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT p.*
            FROM playlists p
            JOIN channels c ON c.id = p.channel_id
            WHERE c.name = ? AND p.enabled = 1
            ORDER BY p.sort_order, p.id
            """,
            (channel_name,),
        )
        return [dict(row) for row in rows]

    def save_discovered_videos(
        self,
        channel_name: str,
        playlist_title: str,
        videos: list[dict],
        mark_new: bool = False,
    ) -> dict:
        """Speichert gefundene Videos und liefert Sync-Statistik zurück.

        Ab v0.8.1 wird ein Video nur einmal in ``videos`` gespeichert.
        Die Zuordnung zu einer oder mehreren Playlists liegt separat in
        ``video_playlists``. Dadurch können gleiche Videos in mehreren
        Playlists vorkommen, ohne doppelte Video-Datensätze zu erzeugen.
        """
        result = {"seen": 0, "new": 0, "updated": 0, "linked": 0}

        if not videos:
            return result

        with self.database.connect() as connection:
            channel_row = connection.execute(
                "SELECT id FROM channels WHERE name = ?",
                (channel_name,),
            ).fetchone()
            channel_id = channel_row["id"] if channel_row else None

            playlist_row = None
            if channel_id is not None and playlist_title:
                playlist_row = connection.execute(
                    """
                    SELECT id FROM playlists
                    WHERE channel_id = ? AND (title = ? OR display_name = ?)
                    ORDER BY id
                    LIMIT 1
                    """,
                    (channel_id, playlist_title, playlist_title),
                ).fetchone()

                if playlist_row is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO playlists (
                            channel_id, playlist_id, title, display_name, url,
                            season, enabled, video_count, new_video_count,
                            sort_order, updated_at
                        )
                        VALUES (?, '', ?, ?, '', 1, 1, 0, 0, 9999, CURRENT_TIMESTAMP)
                        """,
                        (channel_id, playlist_title, playlist_title),
                    )
                    playlist_row = {"id": cursor.lastrowid}

            playlist_db_id = playlist_row["id"] if playlist_row else None

            for video in videos:
                video_id = video.get("id") or video.get("video_id") or ""
                if not video_id:
                    continue

                result["seen"] += 1
                title = video.get("title") or "Ohne Titel"
                url = video.get("url") or f"https://www.youtube.com/watch?v={video_id}"
                description = video.get("description") or ""
                thumbnail_url = video.get("thumbnail") or video.get("thumbnail_url") or ""
                upload_date = str(video.get("upload_date") or video.get("timestamp") or "")
                duration = self._safe_int(video.get("duration"))
                view_count = self._safe_int(video.get("view_count"))
                is_members_only = 1 if self._looks_members_only(video) else 0

                existing = connection.execute(
                    "SELECT id, is_new, is_downloaded FROM videos WHERE video_id = ?",
                    (video_id,),
                ).fetchone()

                if existing:
                    video_db_id = existing["id"]
                    result["updated"] += 1
                    connection.execute(
                        """
                        UPDATE videos
                        SET channel_id = ?,
                            title = ?,
                            url = ?,
                            description = COALESCE(NULLIF(?, ''), description),
                            thumbnail_url = COALESCE(NULLIF(?, ''), thumbnail_url),
                            upload_date = COALESCE(NULLIF(?, ''), upload_date),
                            duration = CASE WHEN ? > 0 THEN ? ELSE duration END,
                            view_count = CASE WHEN ? > 0 THEN ? ELSE view_count END,
                            is_members_only = CASE WHEN ? = 1 THEN 1 ELSE is_members_only END,
                            status = CASE
                                WHEN is_downloaded = 1 THEN 'downloaded'
                                WHEN is_new = 1 THEN 'new'
                                ELSE 'known'
                            END,
                            last_seen_at = CURRENT_TIMESTAMP,
                            last_sync_at = CURRENT_TIMESTAMP
                        WHERE video_id = ?
                        """,
                        (
                            channel_id,
                            title,
                            url,
                            description,
                            thumbnail_url,
                            upload_date,
                            duration,
                            duration,
                            view_count,
                            view_count,
                            is_members_only,
                            video_id,
                        ),
                    )
                else:
                    result["new"] += 1
                    cursor = connection.execute(
                        """
                        INSERT INTO videos (
                            channel_id, video_id, title, url, description,
                            thumbnail_url, upload_date, duration, view_count,
                            status, is_new, is_members_only,
                            first_seen_at, last_seen_at, last_sync_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (
                            channel_id,
                            video_id,
                            title,
                            url,
                            description,
                            thumbnail_url,
                            upload_date,
                            duration,
                            view_count,
                            "new" if mark_new else "known",
                            1 if mark_new else 0,
                            is_members_only,
                        ),
                    )
                    video_db_id = cursor.lastrowid

                if playlist_db_id is not None:
                    before = connection.total_changes
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO video_playlists (
                            video_db_id, playlist_id, first_seen_at, last_seen_at
                        )
                        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (video_db_id, playlist_db_id),
                    )
                    connection.execute(
                        """
                        UPDATE video_playlists
                        SET last_seen_at = CURRENT_TIMESTAMP
                        WHERE video_db_id = ? AND playlist_id = ?
                        """,
                        (video_db_id, playlist_db_id),
                    )
                    if connection.total_changes > before:
                        result["linked"] += 1

            if playlist_db_id is not None:
                playlist_stats = connection.execute(
                    """
                    SELECT
                        COUNT(v.id) AS video_count,
                        SUM(CASE WHEN v.is_new = 1 THEN 1 ELSE 0 END) AS new_video_count
                    FROM video_playlists vp
                    JOIN videos v ON v.id = vp.video_db_id
                    WHERE vp.playlist_id = ?
                    """,
                    (playlist_db_id,),
                ).fetchone()
                connection.execute(
                    """
                    UPDATE playlists
                    SET video_count = ?, new_video_count = ?,
                        last_checked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        int(playlist_stats["video_count"] or 0),
                        int(playlist_stats["new_video_count"] or 0),
                        playlist_db_id,
                    ),
                )

            connection.commit()

        return result

    def mark_video_downloaded(
        self,
        video_id: str,
        filename: str = "",
        has_nfo: bool = False,
        has_thumbnail: bool = False,
        title: str = "",
        url: str = "",
        channel_name: str = "",
    ) -> bool:
        """Markiert ein Video als geladen und legt fehlende Datensätze sicher an."""
        video_id = str(video_id or "").strip()
        if not video_id:
            return False

        filename = str(filename or "").strip()
        title = str(title or "Ohne Titel").strip() or "Ohne Titel"
        url = str(url or f"https://www.youtube.com/watch?v={video_id}").strip()

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE videos
                SET is_downloaded = 1,
                    is_new = 0,
                    status = 'downloaded',
                    download_date = CURRENT_TIMESTAMP,
                    downloaded_filename = COALESCE(NULLIF(?, ''), downloaded_filename),
                    has_nfo = CASE WHEN ? = 1 THEN 1 ELSE has_nfo END,
                    has_thumbnail = CASE WHEN ? = 1 THEN 1 ELSE has_thumbnail END,
                    last_seen_at = CURRENT_TIMESTAMP,
                    last_sync_at = CURRENT_TIMESTAMP
                WHERE video_id = ?
                """,
                (
                    filename,
                    1 if has_nfo else 0,
                    1 if has_thumbnail else 0,
                    video_id,
                ),
            )

            if cursor.rowcount == 0:
                channel_id = None
                if channel_name:
                    channel_row = connection.execute(
                        "SELECT id FROM channels WHERE name = ? ORDER BY id LIMIT 1",
                        (channel_name,),
                    ).fetchone()
                    if channel_row:
                        channel_id = channel_row["id"]

                connection.execute(
                    """
                    INSERT INTO videos (
                        channel_id, video_id, title, url, description,
                        thumbnail_url, upload_date, duration, view_count,
                        status, is_new, is_downloaded, is_members_only,
                        downloaded_filename, download_date,
                        has_nfo, has_thumbnail,
                        first_seen_at, last_seen_at, last_sync_at
                    )
                    VALUES (?, ?, ?, ?, '', '', '', 0, 0,
                            'downloaded', 0, 1, 0,
                            ?, CURRENT_TIMESTAMP, ?, ?,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        channel_id,
                        video_id,
                        title,
                        url,
                        filename,
                        1 if has_nfo else 0,
                        1 if has_thumbnail else 0,
                    ),
                )

            connection.commit()
        return True


    def mark_video_members_only(
        self,
        video_id: str,
        reason: str = "",
        title: str = "",
        url: str = "",
        channel_name: str = "",
    ) -> None:
        """Markiert ein Video als Mitglieder-/Abo-Video.

        Wichtig: Falls das Video noch nicht in der Datenbank steht, wird es
        minimal angelegt. Genau das passiert bei manchen YouTube-Fehlern:
        yt-dlp meldet das Mitglieder-Video erst beim Downloadversuch. Ohne
        diesen Fallback gäbe es keinen Datensatz, den die Bibliothek rot
        markieren könnte.
        """
        video_id = str(video_id or "").strip()
        if not video_id:
            return

        title = str(title or "Mitglieder-Video").strip() or "Mitglieder-Video"
        url = str(url or f"https://www.youtube.com/watch?v={video_id}").strip()

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE videos
                SET is_members_only = 1,
                    status = 'members_only',
                    is_new = 1,
                    last_seen_at = CURRENT_TIMESTAMP,
                    last_sync_at = CURRENT_TIMESTAMP
                WHERE video_id = ?
                """,
                (video_id,),
            )

            if cursor.rowcount == 0:
                channel_id = None
                if channel_name:
                    channel_row = connection.execute(
                        "SELECT id FROM channels WHERE name = ? ORDER BY id LIMIT 1",
                        (channel_name,),
                    ).fetchone()
                    if channel_row:
                        channel_id = channel_row["id"]

                connection.execute(
                    """
                    INSERT INTO videos (
                        channel_id, video_id, title, url, description,
                        thumbnail_url, upload_date, duration, view_count,
                        status, is_new, is_members_only,
                        first_seen_at, last_seen_at, last_sync_at
                    )
                    VALUES (?, ?, ?, ?, ?, '', '', 0, 0,
                            'members_only', 1, 1,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (channel_id, video_id, title, url, reason or "Nur für Kanalmitglieder verfügbar."),
                )

            connection.commit()

    def get_new_videos_for_channel(self, channel_name: str) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT v.*, GROUP_CONCAT(p.title, ', ') AS playlists
            FROM videos v
            JOIN channels c ON c.id = v.channel_id
            LEFT JOIN video_playlists vp ON vp.video_db_id = v.id
            LEFT JOIN playlists p ON p.id = vp.playlist_id
            WHERE c.name = ? AND (v.is_new = 1 OR v.is_members_only = 1)
            GROUP BY v.id
            ORDER BY v.upload_date DESC, v.first_seen_at DESC
            """,
            (channel_name,),
        )
        return [dict(row) for row in rows]

    def search_library_videos(self, query: str = "", status_filter: str = "all", limit: int = 500) -> list[dict]:
        """Liefert die Bibliothek mit frühzeitiger Begrenzung für schnelle Anzeige."""
        conditions = []
        params = []

        query = (query or "").strip()
        if query:
            like = f"%{query}%"
            conditions.append(
                """(
                    v.title LIKE ?
                    OR v.video_id LIKE ?
                    OR c.name LIKE ?
                    OR EXISTS (
                        SELECT 1
                        FROM video_playlists search_vp
                        JOIN playlists search_p ON search_p.id = search_vp.playlist_id
                        WHERE search_vp.video_db_id = v.id
                          AND (search_p.title LIKE ? OR search_p.display_name LIKE ?)
                    )
                )"""
            )
            params.extend([like, like, like, like, like])

        if status_filter == "new":
            conditions.append("v.is_new = 1")
        elif status_filter == "downloaded":
            conditions.append("v.is_downloaded = 1")
        elif status_filter == "members":
            conditions.append("v.is_members_only = 1")

        where_sql = "WHERE " + " AND ".join(conditions) if conditions else ""
        safe_limit = max(1, min(int(limit or 500), 1000))

        sql = f"""
            WITH selected_videos AS (
                SELECT
                    v.id,
                    v.video_id,
                    v.title,
                    v.url,
                    v.upload_date,
                    v.duration,
                    v.description,
                    v.thumbnail_url,
                    v.status,
                    v.is_new,
                    v.is_downloaded,
                    v.is_members_only,
                    v.downloaded_filename,
                    v.first_seen_at,
                    v.last_seen_at,
                    v.last_sync_at,
                    v.has_nfo,
                    v.has_thumbnail,
                    v.channel_id,
                    c.name AS channel_name,
                    c.work_folder AS channel_work_folder,
                    c.target_folder AS channel_target_folder
                FROM videos v
                LEFT JOIN channels c ON c.id = v.channel_id
                {where_sql}
                ORDER BY
                    v.is_new DESC,
                    COALESCE(NULLIF(v.upload_date, ''), v.first_seen_at) DESC,
                    v.first_seen_at DESC
                LIMIT ?
            )
            SELECT
                sv.*,
                (
                    SELECT GROUP_CONCAT(name, ', ')
                    FROM (
                        SELECT DISTINCT
                            COALESCE(NULLIF(p.display_name, ''), p.title) AS name
                        FROM video_playlists vp
                        JOIN playlists p ON p.id = vp.playlist_id
                        WHERE vp.video_db_id = sv.id
                          AND COALESCE(NULLIF(p.display_name, ''), p.title) <> ''
                        ORDER BY p.sort_order, p.id
                    )
                ) AS playlists
            FROM selected_videos sv
            ORDER BY
                sv.is_new DESC,
                COALESCE(NULLIF(sv.upload_date, ''), sv.first_seen_at) DESC,
                sv.first_seen_at DESC
        """
        params.append(safe_limit)
        rows = self.database.fetch_all(sql, tuple(params))
        return [dict(row) for row in rows]

    def _safe_int(self, value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _looks_members_only(self, video: dict) -> bool:
        text = " ".join(
            str(video.get(key, ""))
            for key in ("title", "status", "availability", "error", "message")
        ).lower()
        return any(
            marker in text
            for marker in (
                "members-only",
                "members only",
                "member-only",
                "channel members",
                "kanalmitglied",
                "kanalmitgliedschaft",
                "kanal-abonnenten",
                "abo-video",
                "subscriber-only",
                "subscribers only",
                "premium_only",
                "premium only",
                "requires payment",
                "join this channel",
                "zur kanal unterstützung",
            )
        )

    def get_channel_video_stats(self, channel_name: str) -> dict:
        row = self.database.fetch_one(
            """
            SELECT
                COUNT(DISTINCT v.id) AS videos,
                COUNT(DISTINCT CASE WHEN v.is_new = 1 THEN v.id END) AS new_videos,
                COUNT(DISTINCT CASE WHEN v.is_downloaded = 1 THEN v.id END) AS downloaded_videos,
                COUNT(DISTINCT CASE WHEN v.is_members_only = 1 THEN v.id END) AS members_only_videos,
                COUNT(DISTINCT p.id) AS playlists,
                MAX(p.last_checked_at) AS last_checked_at
            FROM channels c
            LEFT JOIN playlists p ON p.channel_id = c.id
            LEFT JOIN videos v ON v.channel_id = c.id
            WHERE c.name = ?
            """,
            (channel_name,),
        )
        if not row:
            return {
                "videos": 0,
                "new_videos": 0,
                "downloaded_videos": 0,
                "members_only_videos": 0,
                "playlists": 0,
                "last_checked_at": "",
            }

        return {
            "videos": int(row["videos"] or 0),
            "new_videos": int(row["new_videos"] or 0),
            "downloaded_videos": int(row["downloaded_videos"] or 0),
            "members_only_videos": int(row["members_only_videos"] or 0),
            "playlists": int(row["playlists"] or 0),
            "last_checked_at": row["last_checked_at"] or "",
        }


    def create_job(
        self,
        job_type: str,
        title: str = "",
        channel_name: str = "",
        payload: dict | None = None,
        scheduled_at: str = "",
        priority: int = 100,
    ) -> int:
        """Legt einen Job für die spätere Scheduler-/Aufgabenlogik an."""
        payload_text = json.dumps(payload or {}, ensure_ascii=False)
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO jobs (
                    job_type, title, channel_name, status, priority,
                    payload, scheduled_at, created_at
                )
                VALUES (?, ?, ?, 'pending', ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (job_type, title, channel_name, int(priority or 100), payload_text, scheduled_at or ""),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get_jobs(self, status_filter: str = "all", limit: int = 200) -> list[dict]:
        conditions = []
        params = []
        if status_filter and status_filter != "all":
            conditions.append("status = ?")
            params.append(status_filter)
        where_sql = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT id, job_type, title, channel_name, status, priority,
                   payload, error_message, scheduled_at, created_at,
                   started_at, finished_at
            FROM jobs
            {where_sql}
            ORDER BY
                CASE status
                    WHEN 'running' THEN 0
                    WHEN 'pending' THEN 1
                    WHEN 'failed' THEN 2
                    WHEN 'done' THEN 3
                    ELSE 4
                END,
                priority ASC,
                id DESC
            LIMIT ?
        """
        params.append(int(limit or 200))
        rows = self.database.fetch_all(sql, tuple(params))
        return [dict(row) for row in rows]


    def get_job(self, job_id: int) -> dict | None:
        row = self.database.fetch_one(
            """
            SELECT id, job_type, title, channel_name, status, priority,
                   payload, error_message, scheduled_at, created_at,
                   started_at, finished_at
            FROM jobs
            WHERE id = ?
            """,
            (int(job_id),),
        )
        return dict(row) if row else None

    def get_next_pending_job(self) -> dict | None:
        row = self.database.fetch_one(
            """
            SELECT id, job_type, title, channel_name, status, priority,
                   payload, error_message, scheduled_at, created_at,
                   started_at, finished_at
            FROM jobs
            WHERE status = 'pending'
            ORDER BY priority ASC, id ASC
            LIMIT 1
            """
        )
        return dict(row) if row else None

    def update_job_status(self, job_id: int, status: str, error_message: str = "") -> None:
        if status == "running":
            self.database.execute(
                """
                UPDATE jobs
                SET status = ?, error_message = ?, started_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, error_message or "", int(job_id)),
            )
        elif status in {"done", "failed", "cancelled"}:
            self.database.execute(
                """
                UPDATE jobs
                SET status = ?, error_message = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, error_message or "", int(job_id)),
            )
        else:
            self.database.execute(
                "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message or "", int(job_id)),
            )

    def clear_finished_jobs(self) -> int:
        with self.database.connect() as connection:
            before = connection.total_changes
            connection.execute("DELETE FROM jobs WHERE status IN ('done', 'cancelled')")
            connection.commit()
            return max(0, connection.total_changes - before)


    def create_scheduled_task(
        self,
        name: str,
        task_type: str = "sync_channel",
        channel_name: str = "",
        interval_hours: int = 24,
        payload: dict | None = None,
        enabled: bool = True,
        next_run_at: str = "",
    ) -> int:
        """Legt eine Scheduler-Aufgabe an.

        Der erste Lauf ist bewusst sofort fällig, wenn kein next_run_at gesetzt
        wird. So kann eine neue Aufgabe direkt beim nächsten Scheduler-Lauf getestet
        werden.
        """
        payload_text = json.dumps(payload or {}, ensure_ascii=False)
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO scheduled_tasks (
                    name, task_type, channel_name, enabled, interval_hours,
                    payload, next_run_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    name or task_type,
                    task_type,
                    channel_name or "",
                    1 if enabled else 0,
                    int(interval_hours or 24),
                    payload_text,
                    next_run_at or "",
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get_scheduled_tasks(self, enabled_only: bool = False, limit: int = 200) -> list[dict]:
        where_sql = "WHERE enabled = 1" if enabled_only else ""
        rows = self.database.fetch_all(
            f"""
            SELECT id, name, task_type, channel_name, enabled, interval_hours,
                   payload, last_run_at, next_run_at, created_at, updated_at
            FROM scheduled_tasks
            {where_sql}
            ORDER BY enabled DESC,
                     COALESCE(NULLIF(next_run_at, ''), '0000-00-00 00:00:00') ASC,
                     id DESC
            LIMIT ?
            """,
            (int(limit or 200),),
        )
        tasks = [dict(row) for row in rows]
        now = datetime.now()
        for task in tasks:
            task["is_due"] = self._task_is_due(task, now)
        return tasks

    def get_scheduled_task(self, task_id: int) -> dict | None:
        row = self.database.fetch_one(
            """
            SELECT id, name, task_type, channel_name, enabled, interval_hours,
                   payload, last_run_at, next_run_at, created_at, updated_at
            FROM scheduled_tasks
            WHERE id = ?
            """,
            (int(task_id),),
        )
        if not row:
            return None
        task = dict(row)
        task["is_due"] = self._task_is_due(task, datetime.now())
        return task

    def get_due_scheduled_tasks(self, limit: int = 100) -> list[dict]:
        tasks = self.get_scheduled_tasks(enabled_only=True, limit=limit)
        return [task for task in tasks if task.get("is_due")]

    def mark_scheduled_task_run(self, task_id: int) -> None:
        task = self.get_scheduled_task(task_id)
        if not task:
            return
        now = datetime.now()
        next_run = now + timedelta(hours=int(task.get("interval_hours") or 24))
        self.database.execute(
            """
            UPDATE scheduled_tasks
            SET last_run_at = ?, next_run_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                now.strftime("%Y-%m-%d %H:%M:%S"),
                next_run.strftime("%Y-%m-%d %H:%M:%S"),
                int(task_id),
            ),
        )

    def delete_scheduled_task(self, task_id: int) -> None:
        self.database.execute("DELETE FROM scheduled_tasks WHERE id = ?", (int(task_id),))

    def _task_is_due(self, task: dict, now: datetime | None = None) -> bool:
        if not int(task.get("enabled") or 0):
            return False
        next_run_at = (task.get("next_run_at") or "").strip()
        if not next_run_at:
            return True
        now = now or datetime.now()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(next_run_at, fmt) <= now
            except ValueError:
                pass
        return True

    def get_dashboard_stats(self) -> dict:
        """Liefert globale Zahlen für das Dashboard."""
        row = self.database.fetch_one(
            """
            SELECT
                (SELECT COUNT(*) FROM channels) AS channels,
                (SELECT COUNT(*) FROM playlists) AS playlists,
                COUNT(v.id) AS videos,
                SUM(CASE WHEN v.is_new = 1 THEN 1 ELSE 0 END) AS new_videos,
                SUM(CASE WHEN v.is_downloaded = 1 THEN 1 ELSE 0 END) AS downloaded_videos,
                SUM(CASE WHEN v.is_members_only = 1 THEN 1 ELSE 0 END) AS members_only_videos,
                MAX(v.last_sync_at) AS last_sync
            FROM videos v
            """
        )
        db_path = self.database.path
        db_size = "-"
        if db_path.exists():
            size = db_path.stat().st_size
            if size >= 1024 * 1024:
                db_size = f"{size / (1024 * 1024):.1f} MB"
            elif size >= 1024:
                db_size = f"{size / 1024:.1f} KB"
            else:
                db_size = f"{size} B"

        today = datetime.now().strftime("%Y-%m-%d")
        downloads_today = self._count_downloads_since(today)
        active_jobs = self._count_jobs_by_status(("pending", "running"))
        error_jobs = self._count_jobs_by_status(("error", "failed"))
        scheduler_row = self.database.fetch_one("SELECT COUNT(*) AS count FROM scheduled_tasks WHERE enabled = 1")
        scheduler_active = int(scheduler_row["count"] or 0) if scheduler_row else 0

        return {
            "channels": int(row["channels"] or 0) if row else 0,
            "playlists": int(row["playlists"] or 0) if row else 0,
            "videos": int(row["videos"] or 0) if row else 0,
            "new_videos": int(row["new_videos"] or 0) if row else 0,
            "downloaded_videos": int(row["downloaded_videos"] or 0) if row else 0,
            "members_only_videos": int(row["members_only_videos"] or 0) if row else 0,
            "downloads_today": downloads_today,
            "active_jobs": active_jobs,
            "scheduler_status": "Aktiv" if scheduler_active else "Inaktiv",
            "health_status": "OK" if error_jobs == 0 else f"{error_jobs} Fehler",
            "last_sync": row["last_sync"] if row and row["last_sync"] else "",
            "db_size": db_size,
        }

    def get_recent_library_videos(self, status_filter: str = "all", limit: int = 25) -> list[dict]:
        """Liefert kompakte Videolisten für Dashboard/Statistik."""
        conditions = []
        params = []
        if status_filter == "new":
            conditions.append("v.is_new = 1")
        elif status_filter == "downloaded":
            conditions.append("v.is_downloaded = 1")
        elif status_filter == "members":
            conditions.append("v.is_members_only = 1")

        where_sql = ""
        if conditions:
            where_sql = "WHERE " + " AND ".join(conditions)

        sql = f"""
            SELECT
                v.video_id, v.title, v.url, v.upload_date, v.status,
                v.is_new, v.is_downloaded, v.is_members_only,
                v.first_seen_at, v.last_seen_at, v.last_sync_at,
                c.name AS channel_name
            FROM videos v
            LEFT JOIN channels c ON c.id = v.channel_id
            {where_sql}
            ORDER BY
                COALESCE(NULLIF(v.last_sync_at, ''), v.first_seen_at) DESC,
                v.id DESC
            LIMIT ?
        """
        params.append(int(limit or 25))
        rows = self.database.fetch_all(sql, tuple(params))
        return [dict(row) for row in rows]

    def get_statistics_summary(self) -> dict:
        """Liefert ausführliche Statistikdaten für das Statistik-Center."""
        dashboard = self.get_dashboard_stats()

        overview_row = self.database.fetch_one(
            """
            SELECT
                COUNT(*) AS videos,
                SUM(CASE WHEN is_new = 1 THEN 1 ELSE 0 END) AS new_videos,
                SUM(CASE WHEN is_downloaded = 1 THEN 1 ELSE 0 END) AS downloaded_videos,
                SUM(CASE WHEN is_members_only = 1 THEN 1 ELSE 0 END) AS members_only_videos,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_videos,
                AVG(CASE WHEN duration > 0 THEN duration ELSE NULL END) AS avg_duration,
                MAX(last_sync_at) AS last_sync
            FROM videos
            """
        )
        download_row = self.database.fetch_one(
            """
            SELECT
                COUNT(*) AS total_download_jobs,
                SUM(CASE WHEN status IN ('done', 'finished', 'completed', 'success') THEN 1 ELSE 0 END) AS successful_download_jobs,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS failed_download_jobs
            FROM downloads
            """
        )

        videos = int(overview_row["videos"] or 0) if overview_row else 0
        downloaded_videos = int(overview_row["downloaded_videos"] or 0) if overview_row else 0
        error_videos = int(overview_row["error_videos"] or 0) if overview_row else 0
        total_download_jobs = int(download_row["total_download_jobs"] or 0) if download_row else 0
        failed_download_jobs = int(download_row["failed_download_jobs"] or 0) if download_row else 0

        download_rate = self._percent(downloaded_videos, videos)
        error_rate = self._percent(failed_download_jobs or error_videos, total_download_jobs or videos)

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        month_start = now.strftime("%Y-%m-01")

        periods = {
            "downloads_today": self._count_downloads_since(today),
            "downloads_week": self._count_downloads_since(week_start),
            "downloads_month": self._count_downloads_since(month_start),
            "new_today": self._count_new_videos_since(today),
            "new_week": self._count_new_videos_since(week_start),
            "new_month": self._count_new_videos_since(month_start),
            "jobs_active": self._count_jobs_by_status(("pending", "running")),
            "jobs_failed": self._count_jobs_by_status(("error", "failed")),
        }

        downloads_by_day = self._rows(
            """
            SELECT substr(COALESCE(NULLIF(finished_at, ''), NULLIF(started_at, ''), created_at), 1, 10) AS day,
                   COUNT(*) AS count
            FROM downloads
            WHERE day IS NOT NULL AND day <> ''
            GROUP BY day
            ORDER BY day DESC
            LIMIT 14
            """
        )
        downloads_by_day.reverse()

        new_by_week = self._rows(
            """
            SELECT strftime('%Y-W%W', COALESCE(NULLIF(first_seen_at, ''), NULLIF(last_sync_at, ''), 'now')) AS week,
                   COUNT(*) AS count
            FROM videos
            WHERE COALESCE(NULLIF(first_seen_at, ''), last_sync_at) <> ''
            GROUP BY week
            ORDER BY week DESC
            LIMIT 12
            """
        )
        new_by_week.reverse()

        top_channels = self._rows(
            """
            SELECT c.name,
                   COUNT(v.id) AS video_count,
                   SUM(CASE WHEN v.is_downloaded = 1 THEN 1 ELSE 0 END) AS downloaded_count
            FROM channels c
            LEFT JOIN videos v ON v.channel_id = c.id
            GROUP BY c.id, c.name
            ORDER BY video_count DESC, c.name COLLATE NOCASE ASC
            LIMIT 15
            """
        )
        top_playlists = self._rows(
            """
            SELECT COALESCE(NULLIF(p.display_name, ''), p.title) AS title,
                   p.video_count AS video_count,
                   c.name AS channel_name
            FROM playlists p
            LEFT JOIN channels c ON c.id = p.channel_id
            ORDER BY p.video_count DESC, title COLLATE NOCASE ASC
            LIMIT 15
            """
        )
        recent_downloads = self._rows(
            """
            SELECT d.video_id, d.channel_name, d.filename, d.status, d.finished_at, v.title
            FROM downloads d
            LEFT JOIN videos v ON v.video_id = d.video_id
            ORDER BY COALESCE(NULLIF(d.finished_at, ''), NULLIF(d.started_at, ''), d.created_at) DESC,
                     d.id DESC
            LIMIT 20
            """
        )

        return {
            "overview": {
                "channels": dashboard.get("channels", 0),
                "playlists": dashboard.get("playlists", 0),
                "videos": videos,
                "downloaded_videos": downloaded_videos,
                "new_videos": int(overview_row["new_videos"] or 0) if overview_row else 0,
                "members_only_videos": int(overview_row["members_only_videos"] or 0) if overview_row else 0,
                "download_success_rate": download_rate,
                "error_rate": error_rate,
                "avg_duration": self._format_duration(int(overview_row["avg_duration"] or 0) if overview_row else 0),
                "db_size": dashboard.get("db_size", "-"),
                "download_folder_size": self._format_size(self._folder_size(self.base_dir / "downloads")),
                "last_sync": (overview_row["last_sync"] if overview_row and overview_row["last_sync"] else dashboard.get("last_sync", "")) or "-",
            },
            "periods": periods,
            "top_channels": top_channels,
            "top_playlists": top_playlists,
            "recent_downloads": recent_downloads,
            "downloads_by_day": downloads_by_day,
            "new_by_week": new_by_week,
            "max_downloads_by_day": max([int(row.get("count") or 0) for row in downloads_by_day] or [1]),
            "max_new_by_week": max([int(row.get("count") or 0) for row in new_by_week] or [1]),
        }

    def _rows(self, sql: str, parameters: tuple = ()) -> list[dict]:
        return [dict(row) for row in self.database.fetch_all(sql, parameters)]

    def _count_downloads_since(self, date_text: str) -> int:
        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM downloads
            WHERE substr(COALESCE(NULLIF(finished_at, ''), NULLIF(started_at, ''), created_at), 1, 10) >= ?
              AND status NOT IN ('error', 'failed')
            """,
            (date_text,),
        )
        return int(row["count"] or 0) if row else 0

    def _count_new_videos_since(self, date_text: str) -> int:
        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM videos
            WHERE substr(COALESCE(NULLIF(first_seen_at, ''), last_sync_at), 1, 10) >= ?
            """,
            (date_text,),
        )
        return int(row["count"] or 0) if row else 0

    def _count_jobs_by_status(self, statuses: tuple[str, ...]) -> int:
        placeholders = ",".join("?" for _ in statuses)
        row = self.database.fetch_one(
            f"SELECT COUNT(*) AS count FROM jobs WHERE status IN ({placeholders})",
            statuses,
        )
        return int(row["count"] or 0) if row else 0

    def _percent(self, part: int, whole: int) -> str:
        if not whole:
            return "0 %"
        return f"{(part / whole) * 100:.1f} %"

    def _folder_size(self, folder: Path) -> int:
        if not folder.exists():
            return 0
        size = 0
        for path in folder.rglob("*"):
            if path.is_file():
                try:
                    size += path.stat().st_size
                except OSError:
                    pass
        return size

    def _format_size(self, size: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    def _format_duration(self, seconds: int) -> str:
        if seconds <= 0:
            return "-"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours:
            return f"{hours} h {minutes:02} min"
        return f"{minutes} min"
