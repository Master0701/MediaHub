from pathlib import Path

from src.mediahub.tests.test_report import TestResult


def run_tests(base_dir: Path, mode: str):
    results = []
    for rel in ("downloads", "downloads/work", "downloads/Fertig", "logs"):
        path = base_dir / rel
        try:
            path.mkdir(parents=True, exist_ok=True)
            marker = path / ".selftest_write.tmp"
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
            results.append(TestResult("Ordner", rel, "OK", "vorhanden und beschreibbar"))
        except Exception as exc:
            results.append(TestResult("Ordner", rel, "ERROR", f"nicht beschreibbar: {exc}"))
    return results
