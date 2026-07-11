import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


# Windows/Terminal UTF-8 erzwingen, damit Emoji-Ausgaben beim Build nicht abstuerzen.
def _force_utf8_console():
    import os
    import sys
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_force_utf8_console()
from mediahub_version import APP_NAME, APP_VERSION, prepare_version_files
ROOT = Path(__file__).resolve().parent


def _utf8_env():
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env

DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
RELEASE_DIR = ROOT / "release"

DOCS_DIR = ROOT / "assets" / "docs"
PENDING_RELEASE_NOTES = ROOT / "RELEASE_NOTES_PENDING.md"

SPEC_FILE = ROOT / "MediaHub.spec"
EXE_FILE = DIST_DIR / f"{APP_NAME}.exe"

INSTALLER_SCRIPT = ROOT / "installer" / "installer.iss"


def run(command, cwd=ROOT):
    print(" ".join(str(part) for part in command))
    subprocess.run(command, cwd=cwd, check=True, env=_utf8_env())


def clean():
    print("Räume alte Builds auf...")

    for folder in [DIST_DIR, BUILD_DIR, RELEASE_DIR]:
        if folder.exists():
            shutil.rmtree(folder)

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def build_docs():
    print("Erzeuge Handbücher...")

    run([sys.executable, "build_docs.py"])

    if not DOCS_DIR.exists():
        print("WARNUNG: assets/docs wurde nicht erzeugt.")


def build_exe():
    print("Baue MediaHub.exe...")

    run([
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ])

    if not EXE_FILE.exists():
        raise FileNotFoundError(f"EXE wurde nicht gefunden: {EXE_FILE}")

    print(f"EXE erstellt: {EXE_FILE}")


def find_inno_setup():
    candidates = [
        shutil.which("iscc"),
        shutil.which("ISCC"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate

    return None


def build_setup():
    print("Versuche Setup.exe zu bauen...")

    iscc = find_inno_setup()

    if not iscc:
        print("WARNUNG: Inno Setup Compiler wurde nicht gefunden.")
        print("Setup.exe wird übersprungen.")
        return None

    if not INSTALLER_SCRIPT.exists():
        print("WARNUNG: installer/installer.iss wurde nicht gefunden.")
        print("Setup.exe wird übersprungen.")
        return None

    run([iscc, str(INSTALLER_SCRIPT)])

    setup_files = sorted(RELEASE_DIR.glob("MediaHub_Setup*.exe"))

    if not setup_files:
        setup_files = sorted((ROOT / "release").glob("*.exe"))

    if not setup_files:
        print("WARNUNG: Setup.exe wurde nicht gefunden.")
        return None

    setup_file = setup_files[-1]
    print(f"Setup erstellt: {setup_file}")
    return setup_file


def copy_text_files(target_dir: Path):
    for filename in ["README.md", "CHANGELOG.md", "ROADMAP.md"]:
        source = ROOT / filename
        if source.exists():
            shutil.copy2(source, target_dir / filename)


def copy_docs(target_dir: Path):
    if DOCS_DIR.exists():
        shutil.copytree(DOCS_DIR, target_dir / "docs", dirs_exist_ok=True)


def zip_folder(source_dir: Path, zip_path: Path):
    print(f"Erzeuge ZIP: {zip_path.name}")

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zip_file.write(path, path.relative_to(source_dir))


def create_portable_zip():
    portable_dir = RELEASE_DIR / "portable"
    portable_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(EXE_FILE, portable_dir / EXE_FILE.name)
    copy_text_files(portable_dir)
    copy_docs(portable_dir)

    zip_path = RELEASE_DIR / f"MediaHub_v{APP_VERSION}_Portable.zip"
    zip_folder(portable_dir, zip_path)

    return zip_path


def create_setup_zip(setup_file: Path | None):
    if setup_file is None:
        return None

    setup_dir = RELEASE_DIR / "setup"
    setup_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(setup_file, setup_dir / setup_file.name)
    copy_text_files(setup_dir)
    copy_docs(setup_dir)

    zip_path = RELEASE_DIR / f"MediaHub_v{APP_VERSION}_Setup.zip"
    zip_folder(setup_dir, zip_path)

    return zip_path


def create_docs_zip():
    if not DOCS_DIR.exists():
        print("WARNUNG: Keine Handbücher gefunden. Handbuch-ZIP wird übersprungen.")
        return None

    docs_zip = RELEASE_DIR / f"MediaHub_v{APP_VERSION}_Handbuecher.zip"

    print(f"Erzeuge ZIP: {docs_zip.name}")

    if docs_zip.exists():
        docs_zip.unlink()

    with zipfile.ZipFile(docs_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in DOCS_DIR.rglob("*"):
            if path.is_file():
                zip_file.write(path, path.relative_to(DOCS_DIR))

    return docs_zip


def copy_release_notes():
    if not PENDING_RELEASE_NOTES.exists():
        print("WARNUNG: RELEASE_NOTES_PENDING.md wurde nicht gefunden.")
        return None

    target = RELEASE_DIR / "RELEASE_NOTES.md"
    shutil.copy2(PENDING_RELEASE_NOTES, target)
    print(f"Release-Notizen übernommen: {target}")
    return target


def cleanup_temp_release_folders():
    for folder_name in ["portable", "setup"]:
        folder = RELEASE_DIR / folder_name
        if folder.exists():
            shutil.rmtree(folder)


def main():
    prepare_version_files()
    clean()
    build_docs()
    build_exe()

    setup_file = build_setup()

    portable_zip = create_portable_zip()
    setup_zip = create_setup_zip(setup_file)
    docs_zip = create_docs_zip()
    release_notes = copy_release_notes()

    cleanup_temp_release_folders()

    print()
    print("Release fertig:")
    print(f"- {portable_zip}")

    if setup_zip:
        print(f"- {setup_zip}")
    else:
        print("- Setup ZIP übersprungen")

    if docs_zip:
        print(f"- {docs_zip}")
    else:
        print("- Handbuch ZIP übersprungen")

    if release_notes:
        print(f"- {release_notes}")
    else:
        print("- Release-Notizen fehlen")


if __name__ == "__main__":
    main()
