import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEMP_DIR = ROOT / "_test_plugin_build"
PLUGIN_DIR = TEMP_DIR / "hallo_mediahub"
OUTPUT_FILE = ROOT / "Hallo_MediaHub_Test.mhplugin"


def main():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    plugin_json = {
        "id": "hallo_mediahub",
        "name": "Hallo MediaHub",
        "version": "1.0.0",
        "author": "MediaHub Test",
        "description": "Ein Testplugin für den MediaHub Plugin-Manager.",
        "type": "tool",
        "entry": "main.py",
        "icon": "",
        "enabled": True,
        "safe_mode": True,
    }

    (PLUGIN_DIR / "plugin.json").write_text(
        json.dumps(plugin_json, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    (PLUGIN_DIR / "main.py").write_text(
        'print("Hallo von einem MediaHub Testplugin!")\n',
        encoding="utf-8",
    )

    (PLUGIN_DIR / "README.txt").write_text(
        "Dies ist ein Testplugin für MediaHub.\n",
        encoding="utf-8",
    )

    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in PLUGIN_DIR.rglob("*"):
            zip_file.write(file, file.relative_to(TEMP_DIR))

    shutil.rmtree(TEMP_DIR)

    print("✅ Testplugin erstellt:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()