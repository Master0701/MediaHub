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



def update_readme(version: str, release_notes: str) -> None:
    """Aktualisiert den Versionskopf und die aktuellen Änderungen."""
    body = release_body_without_commit_section(release_notes)
    body_lines = [
        line for line in body.splitlines()
        if line.strip().lower() not in {"# änderungen", "# release notes"}
    ]
    body = "\n".join(body_lines).strip()

    text = (
        f"# MediaHub v{version}\n\n"
        "MediaHub ist ein lokales PySide6-Programm zum Verwalten von "
        "YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und "
        "separat installierbaren Erweiterungen.\n\n"
        f"## Änderungen in v{version}\n\n"
        f"{body}\n\n"
        "Die vollständige Versionshistorie steht in "
        "[`CHANGELOG.md`](CHANGELOG.md).\n"
    )
    README.write_text(text, encoding="utf-8")


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

    print(f"=== MediaHub {tag} veröffentlichen ===", flush=True)
    set_version(version)
    ensure_changelog_entry(version)
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
