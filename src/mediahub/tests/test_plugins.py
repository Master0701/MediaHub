import json
from pathlib import Path

from src.mediahub.tests.test_report import TestResult


def run_tests(base_dir: Path, mode: str):
    results = []
    plugins_dir = base_dir / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    manifests = sorted(plugins_dir.glob("*/plugin.json"))
    results.append(TestResult("Plugins", "Plugin-Ordner", "OK", str(plugins_dir)))
    results.append(TestResult("Plugins", "Manifest-Dateien", "OK" if manifests else "WARN", f"{len(manifests)} Plugin(s)"))
    for manifest in manifests:
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            plugin_id = data.get("id") or manifest.parent.name
            results.append(TestResult("Plugins", f"Plugin {plugin_id}", "OK", data.get("name", plugin_id)))
        except Exception as exc:
            results.append(TestResult("Plugins", str(manifest), "ERROR", f"Manifest fehlerhaft: {exc}"))
    return results
