from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def find_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def read_version(base_dir: Path) -> str:
    main_window = base_dir / "src" / "mediahub" / "gui" / "main_window.py"
    if not main_window.exists():
        return "unbekannt"
    text = main_window.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else "unbekannt"


def main() -> int:
    parser = argparse.ArgumentParser(description="MediaHub Selbsttest")
    parser.add_argument("--mode", choices=["quick", "full", "release"], default="quick", help="Testumfang")
    parser.add_argument("--no-save", action="store_true", help="Bericht nicht in logs/ speichern")
    args = parser.parse_args()

    base_dir = find_base_dir()
    sys.path.insert(0, str(base_dir))

    from src.mediahub.tests import MediaHubTestRunner

    runner = MediaHubTestRunner(base_dir=base_dir, version=read_version(base_dir), mode=args.mode)
    report = runner.run()
    print(report.as_text())
    if not args.no_save:
        paths = report.save()
        print(f"\nBericht gespeichert: {paths['text']}")
        print(f"HTML-Bericht: {paths['html']}")
    return 1 if report.error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
