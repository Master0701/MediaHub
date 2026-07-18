import hashlib
import shutil
import subprocess
import sys
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

def _build_env():
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


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
INSTALLER_DIR = ROOT / "installer"

MAIN_FILE = ROOT / "main.py"
ICON_FILE = ROOT / "assets" / "icons" / "mediahub.ico"
VERSION_FILE = ROOT / "version_info.txt"
INSTALLER_SCRIPT = INSTALLER_DIR / "installer.iss"

EXE_FILE = DIST_DIR / f"{APP_NAME}.exe"
SETUP_FILE = RELEASE_DIR / f"{APP_NAME}_Setup_v{APP_VERSION}.exe"

INNO_COMPILER_PATHS = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def print_header(title: str):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def clean():
    print_header("🧹 Räume alte Builds auf")

    for folder in [DIST_DIR, BUILD_DIR, RELEASE_DIR]:
        if folder.exists():
            shutil.rmtree(folder)
            print(f"Entfernt: {folder}")

    spec_file = ROOT / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()
        print(f"Entfernt: {spec_file}")

    RELEASE_DIR.mkdir(exist_ok=True)


def check_required_files() -> bool:
    print_header("🔎 Release-Check")

    checks = [
        ("main.py", MAIN_FILE),
        ("Icon", ICON_FILE),
        ("Versionsdatei", VERSION_FILE),
        ("Installer-Script", INSTALLER_SCRIPT),
        ("Dokumentations-Build", ROOT / "build_docs.py"),
    ]

    ok = True

    for name, path in checks:
        if path.exists():
            print(f"✔ {name}: {path}")
        else:
            print(f"❌ {name} fehlt: {path}")
            ok = False

    return ok


def build_docs():
    print_header("📖 Baue Dokumentation")

    script = ROOT / "build_docs.py"

    if not script.exists():
        raise FileNotFoundError(f"build_docs.py fehlt: {script}")

    subprocess.run([sys.executable, str(script)], check=True, env=_utf8_env())


def build_exe():
    print_header("🚀 Baue OneFile-EXE")

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
        "--icon",
        str(ICON_FILE),
        "--version-file",
        str(VERSION_FILE),
    ]

    assets_dir = ROOT / "assets"
    if assets_dir.exists():
        cmd.extend(["--add-data", f"{assets_dir};assets"])

    cmd.append(str(MAIN_FILE))

    subprocess.run(cmd, check=True, env=_utf8_env())

    if not EXE_FILE.exists():
        raise FileNotFoundError(f"EXE wurde nicht erstellt: {EXE_FILE}")

    print(f"✔ EXE erstellt: {EXE_FILE}")


def find_inno_compiler() -> Path | None:
    for path in INNO_COMPILER_PATHS:
        if path.exists():
            return path
    return None


def build_installer():
    print_header("📦 Baue Installer")

    compiler = find_inno_compiler()

    if compiler is None:
        print("❌ Inno Setup Compiler wurde nicht gefunden.")
        print("Bitte Inno Setup 6 installieren.")
        return False

    subprocess.run([str(compiler), str(INSTALLER_SCRIPT)], check=True, env=_build_env())

    if not SETUP_FILE.exists():
        raise FileNotFoundError(f"Installer wurde nicht erstellt: {SETUP_FILE}")

    print(f"✔ Installer erstellt: {SETUP_FILE}")
    return True


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def write_release_files():
    print_header("📝 Schreibe Release-Dateien")

    readme = RELEASE_DIR / "README.txt"
    changelog = RELEASE_DIR / "CHANGELOG.txt"
    sha_file = RELEASE_DIR / "SHA256.txt"
    third_party = RELEASE_DIR / "THIRD_PARTY_NOTICES.md"
    third_party_licenses = RELEASE_DIR / "THIRD_PARTY_LICENSES.md"

    readme.write_text(
        f"""MediaHub v{APP_VERSION}

Installation:
1. MediaHub_Setup_v{APP_VERSION}.exe starten.
2. Installation abschließen.
3. MediaHub über Desktop oder Startmenü starten.

Dokumentation:
Die aktuelle Dokumentation liegt im Ordner release/docs.

Enthalten sind:
- Kurzanleitung
- Benutzerhandbuch
- Entwicklerhandbuch

Hinweis:
Beim ersten Start legt MediaHub benötigte Ordner wie config, tools, downloads, logs und archive selbst an.

""",
        encoding="utf-8",
    )

    source_third_party = ROOT / "THIRD_PARTY_NOTICES.md"
    if source_third_party.exists():
        shutil.copy2(source_third_party, third_party)
    source_third_party_licenses = ROOT / "THIRD_PARTY_LICENSES.md"
    if source_third_party_licenses.exists():
        shutil.copy2(source_third_party_licenses, third_party_licenses)
    source_licenses = ROOT / "licenses"
    if source_licenses.exists():
        shutil.copytree(source_licenses, RELEASE_DIR / "licenses", dirs_exist_ok=True)

    changelog.write_text(
        f"""MediaHub v{APP_VERSION}

- Erste finale Release-Version
- OneFile-EXE
- Programm-Icon
- Windows-Versionsinformationen
- Installer mit Desktop- und Startmenü-Verknüpfung
- Sauberer Erststart ohne Testdaten
- Automatischer Dokumentations-Build
- Kurzanleitung
- Benutzerhandbuch
- Entwicklerhandbuch
- Help-Center-Index aus Dokumentation

""",
        encoding="utf-8",
    )

    if SETUP_FILE.exists():
        sha_file.write_text(
            f"{sha256_file(SETUP_FILE)}  {SETUP_FILE.name}\n",
            encoding="utf-8",
        )

    print(f"✔ {readme}")
    print(f"✔ {changelog}")
    print(f"✔ {sha_file}")


def final_check():
    print_header("🏁 Finaler Release-Check")

    checks = [
        ("EXE", EXE_FILE),
        ("Installer", SETUP_FILE),
        ("README", RELEASE_DIR / "README.txt"),
        ("CHANGELOG", RELEASE_DIR / "CHANGELOG.txt"),
        ("SHA256", RELEASE_DIR / "SHA256.txt"),
        ("Drittanbieter-Hinweise", RELEASE_DIR / "THIRD_PARTY_NOTICES.md"),
        ("Drittanbieter-Lizenzen", RELEASE_DIR / "THIRD_PARTY_LICENSES.md"),
        ("Lizenzordner", RELEASE_DIR / "licenses"),

        ("Kurzanleitung TXT", RELEASE_DIR / "docs" / "quick" / "KURZANLEITUNG.txt"),
        ("Kurzanleitung HTML", RELEASE_DIR / "docs" / "quick" / "MediaHub_Kurzanleitung.html"),
        ("Kurzanleitung DOCX", RELEASE_DIR / "docs" / "quick" / "MediaHub_Kurzanleitung.docx"),
        ("Kurzanleitung PDF", RELEASE_DIR / "docs" / "quick" / "MediaHub_Kurzanleitung.pdf"),

        ("Benutzerhandbuch TXT", RELEASE_DIR / "docs" / "HANDBUCH.txt"),
        ("Benutzerhandbuch HTML", RELEASE_DIR / "docs" / "MediaHub_Handbuch.html"),
        ("Benutzerhandbuch DOCX", RELEASE_DIR / "docs" / "MediaHub_Handbuch.docx"),
        ("Benutzerhandbuch PDF", RELEASE_DIR / "docs" / "MediaHub_Handbuch.pdf"),

        ("Entwicklerhandbuch TXT", RELEASE_DIR / "docs" / "developer" / "ENTWICKLERHANDBUCH.txt"),
        ("Entwicklerhandbuch HTML", RELEASE_DIR / "docs" / "developer" / "MediaHub_Entwicklerhandbuch.html"),
        ("Entwicklerhandbuch DOCX", RELEASE_DIR / "docs" / "developer" / "MediaHub_Entwicklerhandbuch.docx"),
        ("Entwicklerhandbuch PDF", RELEASE_DIR / "docs" / "developer" / "MediaHub_Entwicklerhandbuch.pdf"),

        ("Help-Index", ROOT / "assets" / "docs" / "help_index.json"),
    ]

    ok = True

    for name, path in checks:
        if path.exists():
            print(f"✔ {name}: {path}")
        else:
            print(f"❌ {name} fehlt: {path}")
            ok = False

    forbidden = [
        DIST_DIR / "config",
        DIST_DIR / "downloads",
        DIST_DIR / "logs",
        DIST_DIR / "archive",
        DIST_DIR / "tools",
        DIST_DIR / "channels.json",
        DIST_DIR / "mediahub.sqlite3",
        DIST_DIR / "ui_state.json",
    ]

    for path in forbidden:
        if path.exists():
            print(f"❌ Unerwünschte Datei/Ordner im Release: {path}")
            ok = False

    if ok:
        print()
        print("✅ MediaHub Release ist bereit.")
    else:
        print()
        print("⚠ Release ist noch nicht sauber.")

    return ok


def main():
    try:
        prepare_version_files()
        if not check_required_files():
            print()
            print("❌ Abbruch: Es fehlen Dateien.")
            return

        clean()
        build_docs()
        build_exe()

        installer_ok = build_installer()

        if installer_ok:
            write_release_files()

        final_check()

    except subprocess.CalledProcessError as error:
        print()
        print("❌ Build-Prozess fehlgeschlagen.")
        print(error)

    except Exception as error:
        print()
        print("❌ Fehler:")
        print(error)


if __name__ == "__main__":
    main()
