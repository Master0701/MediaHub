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
        ROOT / "LICENSE.md",
        ROOT / "THIRD_PARTY_NOTICES.md",
        ROOT / "THIRD_PARTY_LICENSES.md",
        ROOT / "licenses" / "Apache-2.0.txt",
        ROOT / "licenses" / "BSD-2-Clause.txt",
        ROOT / "licenses" / "GPL-2.0.txt",
        ROOT / "licenses" / "LGPL-3.0.txt",
        ROOT / "licenses" / "MIT.txt",
        ROOT / "licenses" / "Unlicense.txt",
        ROOT / "licenses" / "CC-BY-NC-ND-3.0.txt",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Lizenzprüfung fehlgeschlagen. Fehlend oder leer: " + ", ".join(missing))


def git_output(*command: str) -> str:
    result = subprocess.run(
        ["git", *command],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def working_tree_entries() -> list[str]:
    output = git_output(
        "status", "--porcelain=v1", "--untracked-files=all"
    )
    return [line for line in output.splitlines() if line.strip()]


def _normalized_status_path(line: str) -> str:
    """Liest den Dateipfad aus einer git-status --porcelain-Zeile."""
    path = line[3:].strip() if len(line) > 3 else line.strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.replace("\\", "/").strip('"')


def forbidden_release_paths(paths: list[str]) -> list[str]:
    forbidden_prefixes = (
        "tools/", "plugins/", "logs/", "release/", "release_ready/",
        "dist/", "build/", "__pycache__/", ".pytest_cache/", ".mypy_cache/",
    )
    forbidden_fragments = ("/__pycache__/", "/.pytest_cache/", "/.mypy_cache/")
    forbidden_names = ("_patch_backup_", "_release_assistant_", "_renamer_")
    result = []
    for raw_path in paths:
        path = raw_path.replace("\\", "/").lstrip('"')
        if path in {"tools/.gitignore", "plugins/.gitignore"}:
            continue
        if path.startswith(forbidden_prefixes):
            result.append(path)
            continue
        if any(fragment in path for fragment in forbidden_fragments):
            result.append(path)
            continue
        if any(name in path for name in forbidden_names):
            result.append(path)
    return result


def ensure_clean_and_synced_start(branch: str) -> None:
    paths = [_normalized_status_path(line) for line in working_tree_entries()]
    forbidden = forbidden_release_paths(paths)
    if forbidden:
        raise RuntimeError(
            "Release abgebrochen: Laufzeit-, Patch- oder Fremddateien dürfen "
            "nicht veröffentlicht werden.\n\n" + "\n".join(forbidden[:50])
        )

    run("git", "fetch", "origin", branch)
    head = git_output("rev-parse", "HEAD")
    remote = git_output("rev-parse", f"origin/{branch}")
    if head != remote:
        raise RuntimeError(
            f"Release abgebrochen: HEAD und origin/{branch} sind nicht "
            f"identisch.\nLokal: {head}\nRemote: {remote}"
        )


def validate_release_changes() -> list[str]:
    paths = [_normalized_status_path(line) for line in working_tree_entries()]
    forbidden = forbidden_release_paths(paths)
    if forbidden:
        raise RuntimeError(
            "Release abgebrochen: Nicht erlaubte Laufzeit-, Patch- oder "
            "Fremddateien gefunden.\n\n" + "\n".join(forbidden[:50])
        )
    if not paths:
        raise RuntimeError("Release abgebrochen: Keine Änderungen für den Release.")
    return paths


def stage_release_changes(paths: list[str]) -> None:
    run("git", "add", "-A")
    run("git", "add", "-f", "--", PENDING_RELEASE_NOTES.name)
    staged = git_output("diff", "--cached", "--name-only")
    staged_paths = [
        line.strip().replace("\\", "/")
        for line in staged.splitlines()
        if line.strip()
    ]
    forbidden = forbidden_release_paths(staged_paths)
    if forbidden:
        raise RuntimeError(
            "Release abgebrochen: Nicht erlaubte Dateien im Git-Index.\n\n"
            + "\n".join(forbidden[:50])
        )


def ensure_remote_points_to_head(branch: str) -> None:
    head = git_output("rev-parse", "HEAD")
    remote = git_output("rev-parse", f"origin/{branch}")
    if head != remote:
        raise RuntimeError(
            f"Push-Prüfung fehlgeschlagen: origin/{branch} zeigt nicht "
            "auf den neuen Release-Commit."
        )


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
    local_result = subprocess.run(
        ["git", "tag", "--list", tag],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if local_result.stdout.strip():
        return True

    remote_result = subprocess.run(
        [
            "git",
            "ls-remote",
            "--tags",
            "origin",
            f"refs/tags/{tag}",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return bool(remote_result.stdout.strip())


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

    branch = current_branch()
    ensure_clean_and_synced_start(branch)
    print(
        f"Git-Ausgangsprüfung erfolgreich: Programmänderungen erlaubt und synchron mit "
        f"origin/{branch}.",
        flush=True,
    )

    tag = f"v{version}"
    if tag_exists(tag):
        raise SystemExit(f"Der Git-Tag {tag} existiert bereits. Bitte eine neue Version verwenden.")

    if not PENDING_RELEASE_NOTES.exists():
        raise SystemExit("RELEASE_NOTES_PENDING.md fehlt. Das Release wurde nicht gestartet.")
    release_notes = PENDING_RELEASE_NOTES.read_text(
        encoding="utf-8"
    ).strip()

    # Detect replacement question marks caused by broken character
    # encoding before anything is committed, tagged or published.
    #
    # Examples:
    #   Unterst?tzung
    #   f?r
    #   ?nderungen
    import re

    broken_encoding = re.findall(
        r"(?:[A-Za-z]+\?[A-Za-z]+|\?[A-Za-z]{2,})",
        release_notes,
    )

    if broken_encoding:
        examples = ", ".join(
            sorted(set(broken_encoding))[:10]
        )
        raise SystemExit(
            "RELEASE_NOTES_PENDING.md contains suspicious "
            "replacement question marks. Release aborted. "
            f"Examples: {examples}"
        )

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

    if not PENDING_RELEASE_NOTES.exists():
        raise SystemExit("RELEASE_NOTES_PENDING.md fehlt vor dem Git-Commit.")

    generated_paths = validate_release_changes()
    stage_release_changes(generated_paths)
    run("git", "commit", "-m", f"MediaHub {tag}")
    run("git", "push", "origin", branch)
    ensure_remote_points_to_head(branch)

    # Der Tag entsteht erst nach dem geprüften Push und zeigt damit
    # garantiert auf den veröffentlichten Release-Commit.
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
