from pathlib import Path

from src.mediahub.tests.test_report import TestResult

REQUIRED_PATHS = [
    "main.py",
    "src/mediahub/app.py",
    "src/mediahub/gui/main_window.py",
    "src/mediahub/gui/dashboard_panel.py",
    "src/mediahub/gui/recovery_center.py",
    "src/mediahub/gui/help_center.py",
    "src/mediahub/plugins/plugin_api.py",
    "src/mediahub/plugins/plugin_loader.py",
    "requirements.txt",
    "README.md",
    "CHANGELOG.md",
]


def run_tests(base_dir: Path, mode: str):
    results = []
    for rel_path in REQUIRED_PATHS:
        path = base_dir / rel_path
        status = "OK" if path.exists() else "ERROR"
        results.append(TestResult("Projekt", rel_path, status, "vorhanden" if path.exists() else "fehlt"))
    main_window = base_dir / "src/mediahub/gui/main_window.py"
    if main_window.exists():
        text = main_window.read_text(encoding="utf-8", errors="ignore")
        status = "OK" if "APP_VERSION" in text else "WARN"
        results.append(TestResult("Projekt", "Versionskennung", status, "APP_VERSION gefunden" if status == "OK" else "APP_VERSION nicht gefunden"))
    return results
