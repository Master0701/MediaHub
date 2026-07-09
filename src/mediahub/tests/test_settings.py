import json
from pathlib import Path

from src.mediahub.tests.test_report import TestResult


def run_tests(base_dir: Path, mode: str):
    results = []
    config_dir = base_dir / "config"
    results.append(TestResult("Einstellungen", "config-Ordner", "OK" if config_dir.exists() else "ERROR", str(config_dir)))
    for name in ("channels.json", "settings.json"):
        path = config_dir / name
        if not path.exists():
            status = "WARN" if name == "settings.json" else "OK"
            results.append(TestResult("Einstellungen", name, status, "nicht vorhanden" if status == "WARN" else "optional/leer"))
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            results.append(TestResult("Einstellungen", name, "OK", "JSON lesbar"))
        except Exception as exc:
            results.append(TestResult("Einstellungen", name, "ERROR", f"JSON-Fehler: {exc}"))
    return results
