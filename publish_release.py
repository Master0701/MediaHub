from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_INFO = ROOT / "src" / "mediahub" / "app_info.py"
CHANGELOG = ROOT / "CHANGELOG.md"
DEFAULT_RELEASE_NOTES = ROOT / "RELEASE_NOTES_PENDING.md"
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


def read_release_notes() -> tuple[Path, str]:
    configured = os.environ.get("MEDIAHUB_RELEASE_NOTES_FILE", "").strip()
    notes_path = Path(configured) if configured else DEFAULT_RELEASE_NOTES

    if not notes_path.exists():
        raise RuntimeError(
            f"Release-Notizen wurden nicht gefunden: {notes_path}"
        )

    text = notes_path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError(
            f"Release-Notizen sind leer: {notes_path}"
        )

    return notes_path, text


def extract_commit_message(notes: str, version: str) -> str:
    configured = os.environ.get(
        "MEDIAHUB_RELEASE_COMMIT_MESSAGE",
        "",
    ).strip()
    if configured:
        return configured

    lines = notes.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() == "## commit-nachricht":
            for candidate in lines[index + 1:]:
                candidate = candidate.strip()
                if candidate and not candidate.startswith("#"):
                    return candidate
            break

    return f"MediaHub v{version}"


def release_body_without_commit_section(notes: str) -> str:
    lines = notes.splitlines()
    output: list[str] = []

    for line in lines:
        if line.strip().lower() == "## commit-nachricht":
            break
        output.append(line)

    return "\n".join(output).strip()


def ensure_changelog_entry(version: str, release_notes: str) -> None:
    text = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else "# Changelog\n"
    if re.search(rf"^##\s+v{re.escape(version)}(?:\s|$)", text, re.MULTILINE):
        return
    body = release_body_without_commit_section(release_notes)
    heading = f"## v{version}\n\n{body}\n\n"
    if text.startswith("# Changelog"):
        first_break = text.find("\n")
        text = text[: first_break + 1] + "\n" + heading + text[first_break + 1 :].lstrip("\n")
    else:
        text = "# Changelog\n\n" + heading + text
    CHANGELOG.write_text(text, encoding="utf-8")


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
    notes_path, release_notes = read_release_notes()
    commit_message = extract_commit_message(release_notes, version)

    set_version(version)
    ensure_changelog_entry(version, release_notes)
    run(sys.executable, "mediahub_version.py")

    if not args.skip_local_build:
        run(sys.executable, "build_release.py")

    branch = current_branch()
    run("git", "add", "-A")
    run("git", "commit", "-m", commit_message)
    run("git", "push", "origin", branch)
    run("git", "tag", "-a", tag, "-m", f"MediaHub {tag}")
    run("git", "push", "origin", tag)

    release_notes_target = ROOT / "release" / "RELEASE_NOTES.md"
    if release_notes_target.exists():
        print(f"Release-Notizen für GitHub vorbereitet: {release_notes_target}", flush=True)

    print("\nFertig: Der Tag wurde zu GitHub übertragen.", flush=True)
    print("GitHub Actions baut nun Setup, Portable-ZIP und Handbücher und erstellt das Release.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
