import json
import zipfile
from pathlib import Path

from src.mediahub.tests.test_report import TestResult


def run_tests(base_dir: Path, mode: str):
    results = []
    backups = base_dir / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    results.append(TestResult("Recovery", "Backup-Ordner", "OK", str(backups)))
    existing = sorted(backups.glob("*.zip"))
    results.append(TestResult("Recovery", "Vorhandene Backups", "OK" if existing else "WARN", f"{len(existing)} Backup(s) gefunden"))
    if mode in ("full", "release"):
        test_zip = backups / "selftest_backup_probe.zip"
        try:
            manifest = {"mediahub_version": "selftest", "backup_version": 1, "selftest": True}
            with zipfile.ZipFile(test_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            with zipfile.ZipFile(test_zip, "r") as zf:
                data = json.loads(zf.read("manifest.json").decode("utf-8"))
            status = "OK" if data.get("selftest") else "ERROR"
            results.append(TestResult("Recovery", "Backup-Probe", status, "Test-ZIP mit manifest.json lesbar"))
        except Exception as exc:
            results.append(TestResult("Recovery", "Backup-Probe", "ERROR", str(exc)))
        finally:
            test_zip.unlink(missing_ok=True)
    return results
