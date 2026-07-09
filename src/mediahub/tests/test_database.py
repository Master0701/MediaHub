import sqlite3
from pathlib import Path

from src.mediahub.tests.test_report import TestResult


def run_tests(base_dir: Path, mode: str):
    results = []
    db_path = base_dir / "config" / "mediahub.sqlite3"
    if not db_path.exists():
        return [TestResult("Datenbank", "SQLite-Datei", "WARN", "config/mediahub.sqlite3 nicht vorhanden")]
    results.append(TestResult("Datenbank", "SQLite-Datei", "OK", f"{db_path.stat().st_size} Bytes"))
    try:
        with sqlite3.connect(db_path) as con:
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            status = "OK" if str(integrity).lower() == "ok" else "ERROR"
            results.append(TestResult("Datenbank", "Integrität", status, str(integrity)))
            tables = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            results.append(TestResult("Datenbank", "Tabellen", "OK" if tables else "WARN", f"{tables} Tabelle(n)"))
    except Exception as exc:
        results.append(TestResult("Datenbank", "SQLite-Zugriff", "ERROR", str(exc)))
    return results
