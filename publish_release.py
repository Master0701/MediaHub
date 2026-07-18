from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_INFO = ROOT / "src" / "mediahub" / "app_info.py"
PENDING_RELEASE_NOTES = ROOT / "RELEASE_NOTES_PENDING.md"
CHANGELOG = ROOT / "CHANGELOG.md"
README = ROOT / "README.md"
VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']\s*$', re.MULTILINE)
VALID_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def run(*command: str) -> None:
    print("$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def set_version(version: str) -> None:
    text = APP_INFO.read_text(encoding="utf-8")
    if not VERSION_RE.search(text):
        raise RuntimeError(f"APP_VERSION wurde nicht gefunden: {APP_INFO}")
    updated = VERSION_RE.sub(f'APP_VERSION = "{version}"', text, count=1)
    APP_INFO.write_text(updated, encoding="utf-8")


def ensure_changelog_entry(version: str) -> None:
    text = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else "# Changelog\n"
    if re.search(rf"^##\s+v{re.escape(version)}(?:\s|$)", text, re.MULTILINE):
        return
    heading = (
        f"## v{version}\n\n"
        "### Neu\n\n"
        "- Release über den MediaHub Release-Assistenten erstellt.\n\n"
        "### Verbessert\n\n"
        "- Versions-, Build- und GitHub-Release-Ablauf automatisiert.\n\n"
    )
    if text.startswith("# Changelog"):
        first_break = text.find("\n")
        text = text[: first_break + 1] + "\n" + heading + text[first_break + 1 :].lstrip("\n")
    else:
        text = "# Changelog\n\n" + heading + text
    CHANGELOG.write_text(text, encoding="utf-8")



def release_body_without_commit_section(release_notes: str) -> str:
    """Entfernt interne Commit-Angaben aus den öffentlichen Release-Notizen."""
    public_lines: list[str] = []
    skipping_commit_section = False

    for line in release_notes.splitlines():
        normalized = line.strip().lower()
        if normalized == "## commit-nachricht":
            skipping_commit_section = True
            continue
        if skipping_commit_section:
            # Die Commit-Nachricht steht im MediaHub-Workflow am Ende. Sollte
            # später doch noch ein weiterer Hauptabschnitt folgen, wird er
            # wieder als öffentlicher Inhalt übernommen.
            if line.startswith("## ") and normalized != "## commit-nachricht":
                skipping_commit_section = False
            else:
                continue
        public_lines.append(line)

    return "\n".join(public_lines).strip()


def update_readme(version: str, release_notes: str) -> None:
    """Aktualisiert Versionskopf und aktuellen Änderungsblock der README."""
    body = release_body_without_commit_section(release_notes)
    body_lines = [
        line for line in body.splitlines()
        if line.strip().lower() not in {"# änderungen", "# release notes"}
    ]
    body = "\n".join(body_lines).strip()
    if not body:
        raise RuntimeError("Die öffentlichen Release-Notizen sind leer.")

    old_text = README.read_text(encoding="utf-8") if README.exists() else ""
    history_marker = "Die vollständige Versionshistorie steht in [`CHANGELOG.md`](CHANGELOG.md)."
    marker_index = old_text.find(history_marker)

    if marker_index >= 0:
        stable_tail = old_text[marker_index:].lstrip()
    else:
        stable_tail = (
            history_marker + "\n\n"
            "## Start aus dem Quellcode\n\n"
            "```powershell\n"
            "python -m pip install -r requirements.txt\n"
            "python main.py\n"
            "```\n"
        )

    updated = (
        f"# MediaHub v{version}\n\n"
        "MediaHub ist ein lokales PySide6-Programm zum Verwalten von "
        "YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und "
        "separat installierbaren Erweiterungen.\n\n"
        f"## Neu und verbessert in v{version}\n\n"
        f"{body}\n\n"
        f"{stable_tail.rstrip()}\n"
    )
    README.write_text(updated, encoding="utf-8")


def verify_release_files(version: str) -> None:
    """Prüft vor Build und Commit die zentralen UTF-8-/Versionsdateien."""
    expected_header = f"# MediaHub v{version}"
    readme_text = README.read_text(encoding="utf-8")
    if not readme_text.startswith(expected_header):
        raise RuntimeError(f"README-Version wurde nicht korrekt aktualisiert: {expected_header}")

    app_info_text = APP_INFO.read_text(encoding="utf-8")
    match = VERSION_RE.search(app_info_text)
    if not match or match.group(1) != version:
        raise RuntimeError("APP_VERSION stimmt nach der Aktualisierung nicht mit der Release-Version überein.")

    # Das Lesen mit encoding='utf-8' ist zugleich die verbindliche UTF-8-Prüfung.
    for path in (README, CHANGELOG, PENDING_RELEASE_NOTES, APP_INFO):
        path.read_text(encoding="utf-8")


def verify_license_files() -> None:
    required = [
        ROOT / "THIRD_PARTY_NOTICES.md",
        ROOT / "THIRD_PARTY_LICENSES.md",
        ROOT / "licenses" / "Apache-2.0.txt",
        ROOT / "licenses" / "BSD-2-Clause.txt",
        ROOT / "licenses" / "GPL-2.0.txt",
        ROOT / "licenses" / "LGPL-3.0.txt",
        ROOT / "licenses" / "MIT.txt",
        ROOT / "licenses" / "Unlicense.txt",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Lizenzprüfung fehlgeschlagen. Fehlend oder leer: " + ", ".join(missing))

def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    branch = result.stdout.strip()
    if not branch:
        raise RuntimeError("Aktueller Git-Branch konnte nicht ermittelt werden.")
    return branch


def tag_exists(tag: str) -> bool:
    result = subprocess.run(["git", "tag", "--list", tag], cwd=ROOT, check=True,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    return bool(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="MediaHub vollständig bauen und auf GitHub veröffentlichen.")
    parser.add_argument("version", help="Neue Version, z. B. 1.0.4")
    parser.add_argument("--skip-local-build", action="store_true", help="Lokalen Release-Build überspringen")
    args = parser.parse_args()

    version = args.version.strip().lstrip("v")
    if not VALID_VERSION_RE.fullmatch(version):
        raise SystemExit("Ungültige Version. Erwartet wird z. B. 1.0.4 oder 1.0.4-beta.1")

    if not (ROOT / ".git").exists():
        raise SystemExit("Kein Git-Repository gefunden. Starte den Assistenten aus dem MediaHub-Quellordner.")

    tag = f"v{version}"
    if tag_exists(tag):
        raise SystemExit(f"Der Git-Tag {tag} existiert bereits. Bitte eine neue Version verwenden.")

    if not PENDING_RELEASE_NOTES.exists():
        raise SystemExit("RELEASE_NOTES_PENDING.md fehlt. Das Release wurde nicht gestartet.")
    release_notes = PENDING_RELEASE_NOTES.read_text(encoding="utf-8").strip()
    if not release_notes:
        raise SystemExit("RELEASE_NOTES_PENDING.md ist leer. Das Release wurde nicht gestartet.")

    print(f"=== MediaHub {tag} veröffentlichen ===", flush=True)
    verify_license_files()
    print("Lizenzprüfung erfolgreich.", flush=True)
    set_version(version)
    ensure_changelog_entry(version)
    update_readme(version, release_notes)
    verify_release_files(version)
    print(f"README und zentrale Versionsdateien für {tag} aktualisiert (UTF-8 OK).", flush=True)
    run(sys.executable, "mediahub_version.py")

    if not args.skip_local_build:
        run(sys.executable, "build_release.py")

    branch = current_branch()
    run("git", "add", "-A")

    # Die temporären Release-Notizen stehen absichtlich in .gitignore.
    # Für den Release-Commit werden sie trotzdem aufgenommen, damit der
    # GitHub-Actions-Checkout des Tags die Datei sicher enthält.
    if not PENDING_RELEASE_NOTES.exists():
        raise SystemExit("RELEASE_NOTES_PENDING.md fehlt vor dem Git-Commit.")
    run("git", "add", "-f", str(PENDING_RELEASE_NOTES.name))

    run("git", "commit", "-m", f"MediaHub {tag}")
    run("git", "push", "origin", branch)
    run("git", "tag", "-a", tag, "-m", f"MediaHub {tag}")
    run("git", "push", "origin", tag)

    # Auf dem Hauptbranch bleibt die temporäre Datei nicht liegen. Der Tag
    # verweist weiterhin auf den Release-Commit, in dem sie vorhanden ist.
    if PENDING_RELEASE_NOTES.exists():
        PENDING_RELEASE_NOTES.unlink()
        run("git", "add", "-u", str(PENDING_RELEASE_NOTES.name))
        run("git", "commit", "-m", f"Temporäre Release-Notizen nach {tag} entfernen")
        run("git", "push", "origin", branch)

    print("\nFertig: Der Tag wurde zu GitHub übertragen.", flush=True)
    print("GitHub Actions baut nun Setup, Portable-ZIP und Handbücher und erstellt das Release.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
