from src.mediahub.storage.database import Database


class MigrationManager:
    """Legt die SQLite-Struktur an und aktualisiert sie vorsichtig."""

    CURRENT_SCHEMA_VERSION = 7

    def __init__(self, database: Database):
        self.database = database

    def migrate(self) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    profile TEXT NOT NULL DEFAULT 'Plex',
                    audio_only INTEGER NOT NULL DEFAULT 0,
                    filename_template TEXT NOT NULL DEFAULT '{title} S{season:02}E{episode:02}',
                    work_folder TEXT NOT NULL DEFAULT '',
                    target_folder TEXT NOT NULL DEFAULT '',
                    poster TEXT NOT NULL DEFAULT '',
                    fanart TEXT NOT NULL DEFAULT '',
                    container TEXT NOT NULL DEFAULT 'MKV',
                    resolution TEXT NOT NULL DEFAULT '1080p',
                    audio_format TEXT NOT NULL DEFAULT 'M4A',
                    create_nfo INTEGER NOT NULL DEFAULT 1,
                    create_poster INTEGER NOT NULL DEFAULT 1,
                    create_fanart INTEGER NOT NULL DEFAULT 1,
                    clean_work_folder INTEGER NOT NULL DEFAULT 1,
                    playlist_folder_mode TEXT NOT NULL DEFAULT 'Nur Staffeln',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    playlist_id TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    season INTEGER NOT NULL DEFAULT 1,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_checked_at TEXT NOT NULL DEFAULT '',
                    video_count INTEGER NOT NULL DEFAULT 0,
                    new_video_count INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
                )
                """
            )
            self._ensure_column(connection, "playlists", "display_name", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "playlists", "season", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(connection, "playlists", "video_count", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "playlists", "new_video_count", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "playlists", "sort_order", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "playlists", "updated_at", "TEXT NOT NULL DEFAULT ''")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    video_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    thumbnail_url TEXT NOT NULL DEFAULT '',
                    upload_date TEXT NOT NULL DEFAULT '',
                    duration INTEGER NOT NULL DEFAULT 0,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'known',
                    is_new INTEGER NOT NULL DEFAULT 1,
                    is_downloaded INTEGER NOT NULL DEFAULT 0,
                    download_date TEXT NOT NULL DEFAULT '',
                    downloaded_filename TEXT NOT NULL DEFAULT '',
                    has_nfo INTEGER NOT NULL DEFAULT 0,
                    has_thumbnail INTEGER NOT NULL DEFAULT 0,
                    is_members_only INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_sync_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE SET NULL
                )
                """
            )
            # Spalten aus älteren Alpha-Ständen vorsichtig nachziehen.
            self._ensure_column(connection, "videos", "description", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "videos", "thumbnail_url", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "videos", "view_count", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "videos", "status", "TEXT NOT NULL DEFAULT 'known'")
            self._ensure_column(connection, "videos", "is_new", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(connection, "videos", "is_downloaded", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "videos", "download_date", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "videos", "downloaded_filename", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "videos", "has_nfo", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "videos", "has_thumbnail", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "videos", "is_members_only", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "videos", "first_seen_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "videos", "last_seen_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "videos", "last_sync_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "videos", "checksum", "TEXT NOT NULL DEFAULT ''")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS video_playlists (
                    video_db_id INTEGER NOT NULL,
                    playlist_id INTEGER NOT NULL,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (video_db_id, playlist_id),
                    FOREIGN KEY(video_db_id) REFERENCES videos(id) ON DELETE CASCADE,
                    FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    channel_name TEXT NOT NULL DEFAULT '',
                    playlist_title TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    filename TEXT NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_type TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    channel_name TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority INTEGER NOT NULL DEFAULT 100,
                    payload TEXT NOT NULL DEFAULT '{}',
                    error_message TEXT NOT NULL DEFAULT '',
                    scheduled_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._ensure_column(connection, "jobs", "priority", "INTEGER NOT NULL DEFAULT 100")
            self._ensure_column(connection, "jobs", "payload", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(connection, "jobs", "error_message", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "jobs", "scheduled_at", "TEXT NOT NULL DEFAULT ''")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    task_type TEXT NOT NULL DEFAULT 'sync_channel',
                    channel_name TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    interval_hours INTEGER NOT NULL DEFAULT 24,
                    payload TEXT NOT NULL DEFAULT '{}',
                    last_run_at TEXT NOT NULL DEFAULT '',
                    next_run_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_column(connection, "scheduled_tasks", "enabled", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(connection, "scheduled_tasks", "interval_hours", "INTEGER NOT NULL DEFAULT 24")
            self._ensure_column(connection, "scheduled_tasks", "payload", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(connection, "scheduled_tasks", "last_run_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "scheduled_tasks", "next_run_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "scheduled_tasks", "updated_at", "TEXT NOT NULL DEFAULT ''")

            connection.execute(
                """
                INSERT OR REPLACE INTO app_meta (key, value)
                VALUES ('schema_version', ?)
                """,
                (str(self.CURRENT_SCHEMA_VERSION),),
            )
            connection.commit()

    def _ensure_column(self, connection, table: str, column: str, definition: str) -> None:
        existing_columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in existing_columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
