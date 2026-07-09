from pathlib import Path

from src.mediahub.tests.test_report import TestResult


HELP_OUTPUTS = [
    ("Benutzerhandbuch PDF", "assets/docs/MediaHub_Handbuch.pdf", "OK"),
    ("Benutzerhandbuch HTML", "assets/docs/MediaHub_Handbuch.html", "OK"),
    ("Benutzerhandbuch TXT", "assets/docs/HANDBUCH.txt", "OK"),
    ("Hilfe-Index", "assets/docs/help_index.json", "OK"),
    ("Kurzanleitung PDF", "assets/docs/quick/MediaHub_Kurzanleitung.pdf", "WARN"),
    ("Entwicklerhandbuch PDF", "assets/docs/developer/MediaHub_Entwicklerhandbuch.pdf", "WARN"),
]


def run_tests(base_dir: Path, mode: str):
    results = []

    for name, rel_path, missing_status in HELP_OUTPUTS:
        path = base_dir / rel_path
        results.append(
            TestResult(
                "Hilfe",
                name,
                "OK" if path.exists() else missing_status,
                str(path) if path.exists() else f"fehlt: {path}",
            )
        )

    changelog = base_dir / "CHANGELOG.md"
    readme = base_dir / "README.md"
    results.append(TestResult("Hilfe", "CHANGELOG.md", "OK" if changelog.exists() else "ERROR", str(changelog)))
    results.append(TestResult("Hilfe", "README.md", "OK" if readme.exists() else "WARN", str(readme)))

    if changelog.exists():
        text = changelog.read_text(encoding="utf-8", errors="ignore")
        has_history = "rc" in text.lower() or "version" in text.lower() or "mediahub" in text.lower()
        results.append(
            TestResult(
                "Hilfe",
                "Versionshistorie",
                "OK" if has_history else "WARN",
                "Changelog enthält Versionshinweise" if has_history else "keine Versionshinweise erkannt",
            )
        )

    return results
