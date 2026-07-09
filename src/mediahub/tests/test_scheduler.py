import sqlite3
from pathlib import Path

from src.mediahub.tests.test_report import TestResult


def run_tests(base_dir: Path, mode: str):
    db_path = base_dir / "config" / "mediahub.sqlite3"
    if not db_path.exists():
        return [TestResult("Scheduler", "Datenbank", "WARN", "keine Datenbank vorhanden")]
    try:
        with sqlite3.connect(db_path) as con:
            tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        has_scheduler = any("sched" in name.lower() or "task" in name.lower() or "job" in name.lower() for name in tables)
        return [TestResult("Scheduler", "Scheduler-Tabellen", "OK" if has_scheduler else "WARN", ", ".join(tables[:12]) or "keine Tabellen")]
    except Exception as exc:
        return [TestResult("Scheduler", "Scheduler-Prüfung", "ERROR", str(exc))]
