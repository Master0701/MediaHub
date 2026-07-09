import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

APP_NAME = "MediaHub"

DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"

MAIN_FILE = ROOT / "main.py"
ICON_FILE = ROOT / "assets" / "icons" / "mediahub.ico"
VERSION_FILE = ROOT / "version_info.txt"


def clean():
    print("🧹 Räume alte Builds auf...")

    for folder in [DIST_DIR, BUILD_DIR]:
        if folder.exists():
            shutil.rmtree(folder)

    spec_file = ROOT / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()


def build_exe():
    print("🚀 Baue OneFile-EXE...")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--windowed",
        "--onefile",
        "--name",
        APP_NAME,
    ]

    if ICON_FILE.exists():
        print(f"🎨 Icon gefunden: {ICON_FILE}")
        cmd.extend(["--icon", str(ICON_FILE)])
    else:
        print(f"❌ Icon nicht gefunden: {ICON_FILE}")

    if VERSION_FILE.exists():
        print(f"🏷 Versionsdatei gefunden: {VERSION_FILE}")
        cmd.extend(["--version-file", str(VERSION_FILE)])
    else:
        print(f"❌ Versionsdatei nicht gefunden: {VERSION_FILE}")

    assets_dir = ROOT / "assets"
    if assets_dir.exists():
        cmd.extend(["--add-data", f"{assets_dir};assets"])

    cmd.append(str(MAIN_FILE))

    subprocess.run(cmd, check=True)


def cleanup_release():
    print("🧽 Entferne versehentliche Benutzerdaten aus dist...")

    forbidden_items = [
        DIST_DIR / "config",
        DIST_DIR / "data",
        DIST_DIR / "logs",
        DIST_DIR / "downloads",
        DIST_DIR / "archive",
        DIST_DIR / "cache",
        DIST_DIR / "channels.json",
        DIST_DIR / "mediahub.sqlite3",
        DIST_DIR / "mediahub.db",
        DIST_DIR / "mediahub.sqlite",
        DIST_DIR / "database.db",
        DIST_DIR / "ui_state.json",
        DIST_DIR / "config.json",
    ]

    for path in forbidden_items:
        if path.is_dir():
            shutil.rmtree(path)
            print(f"  entfernt: {path}")
        elif path.is_file():
            path.unlink()
            print(f"  entfernt: {path}")


def main():
    if not MAIN_FILE.exists():
        print("❌ main.py wurde nicht gefunden.")
        return

    clean()
    build_exe()
    cleanup_release()

    exe_path = DIST_DIR / f"{APP_NAME}.exe"

    print()
    if exe_path.exists():
        print("✅ OneFile-Build erfolgreich!")
        print(exe_path)
    else:
        print("❌ EXE wurde nicht gefunden.")


if __name__ == "__main__":
    main()