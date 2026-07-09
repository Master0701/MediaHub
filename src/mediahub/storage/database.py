import sqlite3
from pathlib import Path
from typing import Iterable, Optional


class Database:
    """Kleine SQLite-Hilfsklasse für die spätere MediaHub-Datenbank.

    Diese Klasse wird in v0.6.1 nur vorbereitet. Die bestehenden Kanäle
    bleiben vorerst in channels.json, damit das Programm stabil weiterläuft.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def execute(self, sql: str, parameters: Optional[Iterable] = None) -> None:
        with self.connect() as connection:
            connection.execute(sql, tuple(parameters or []))
            connection.commit()

    def fetch_all(self, sql: str, parameters: Optional[Iterable] = None) -> list[sqlite3.Row]:
        with self.connect() as connection:
            cursor = connection.execute(sql, tuple(parameters or []))
            return cursor.fetchall()

    def fetch_one(self, sql: str, parameters: Optional[Iterable] = None) -> sqlite3.Row | None:
        with self.connect() as connection:
            cursor = connection.execute(sql, tuple(parameters or []))
            return cursor.fetchone()
