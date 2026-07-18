import json
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path


class ReleaseService:
    """Erstellt sichere Release-Vorbereitungen ohne private Arbeitsdaten zu löschen."""

    def __init__(self, base_dir: Path, app_version: str = "", logger=None):
        self.base_dir = Path(base_dir)
        self.app_version = app_version
        self.logger = logger
        self.logs_dir = self.base_dir / "logs"
        self.release_dir = self.base_dir / "release_ready"

    def prepare_release(self, include_sample_channel: bool = False):
        started = datetime.now()
        stamp = started.strftime("%Y-%m-%d_%H-%M-%S")
        target = self.release_dir / f"MediaHub_{self._safe_version()}_{stamp}"
        target.mkdir(parents=True, exist_ok=True)
        details, warnings, errors = [], [], []

        for rel in ("config", "downloads", "downloads/Fertig", "downloads/work", "logs", "Backups", "plugins", "docs", "assets", "assets/icons", "assets/themes", "tools"):
            (target / rel).mkdir(parents=True, exist_ok=True)
        details.append("Standardordner erzeugt")

        channels = []
        if include_sample_channel:
            channels = [{"name": "Beispielkanal", "url": "https://www.youtube.com/@example", "mode": "preview", "playlists": [], "enabled": False}]
        self._write_json(target / "config" / "channels.json", {"version": 2, "channels": channels})
        details.append("channels.json ohne private Kanaele erstellt")

        settings = {
            "download_dir": "downloads/Fertig", "work_dir": "downloads/work", "backup_dir": "Backups", "log_dir": "logs",
            "plex_enabled": False, "plex_url": "", "plex_token": "",
            "auto_backup": {"enabled": False, "interval": "weekly", "keep": 10},
            "first_start_done": False,
        }
        self._write_json(target / "config" / "settings.json", settings)
        details.append("settings.json mit Standardwerten erstellt")
        self._create_empty_database(target / "config" / "mediahub.sqlite3")
        details.append("leere SQLite-Datenbank erstellt")

        for name in ("README.md", "CHANGELOG.md", "ROADMAP.md", "TODO.md", "requirements.txt", "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_LICENSES.md", ".gitignore", "main.py"):
            src = self.base_dir / name
            if src.exists():
                shutil.copy2(src, target / name)
                details.append(f"{name} kopiert")
            elif name not in ("TODO.md", "ROADMAP.md", ".gitignore"):
                warnings.append(f"{name} nicht gefunden")

        license_file = self.base_dir / "LICENSE"
        if license_file.exists():
            shutil.copy2(license_file, target / "LICENSE")
            details.append("LICENSE kopiert")
        else:
            (target / "LICENSE.txt").write_text("MediaHub\n\nLizenz noch festlegen, bevor MediaHub öffentlich verteilt wird.\n", encoding="utf-8")
            warnings.append("LICENSE fehlt - Platzhalter LICENSE.txt erstellt")

        docs_src = self.base_dir / "docs" / "MediaHub_Anleitung.pdf"
        if docs_src.exists():
            shutil.copy2(docs_src, target / "docs" / "MediaHub_Anleitung.pdf")
            details.append("PDF-Handbuch kopiert")
        else:
            warnings.append("PDF-Handbuch fehlt")

        for rel, content in {
            "logs/README.txt": "Hier speichert MediaHub Laufzeit-Logs.\n",
            "downloads/README.txt": "Hier legt MediaHub heruntergeladene Medien ab.\n",
            "Backups/README.txt": "Hier legt MediaHub Backups ab.\n",
            "plugins/README.txt": "Hier koennen MediaHub-Plugins installiert werden.\n",
        }.items():
            (target / rel).write_text(content, encoding="utf-8")

        self._copy_tree_if_exists(self.base_dir / "src", target / "src", details, "src")
        self._copy_tree_if_exists(self.base_dir / "assets", target / "assets", details, "assets")
        self._copy_tree_if_exists(self.base_dir / "plugins", target / "plugins", details, "plugins")
        self._copy_tree_if_exists(self.base_dir / "tools", target / "tools", details, "tools")
        self._copy_tree_if_exists(self.base_dir / "licenses", target / "licenses", details, "licenses")
        self.create_build_files(target)
        details.append("Build-Dateien im Release-Verzeichnis erstellt")

        report = {"version": self.app_version, "created": started.isoformat(timespec="seconds"), "target": str(target), "ok": len(errors) == 0, "warnings": warnings, "errors": errors, "details": details}
        self._write_reports(report, stamp)
        return report

    def build_release_package(self):
        report = self.prepare_release(include_sample_channel=False)
        target = Path(report.get("target", ""))
        if not target.exists():
            report.setdefault("errors", []).append("Release-Verzeichnis wurde nicht erstellt")
            report["ok"] = False
            return report
        zip_path = target.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in target.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(target.parent))
        report["zip"] = str(zip_path)
        report.setdefault("details", []).append(f"Release-ZIP erstellt: {zip_path.name}")
        self._write_reports(report, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        return report

    def create_build_files(self, target: Path | None = None):
        target = Path(target) if target else self.base_dir
        build = target / "build"
        build.mkdir(parents=True, exist_ok=True)
        (build / "MediaHub.spec").write_text(self._pyinstaller_spec(), encoding="utf-8")
        exe_bat = "\r\n".join([
            "@echo off",
            "cd /d %~dp0..",
            "python -m pip install -r requirements.txt",
            "python -m pip install pyinstaller",
            "python -m PyInstaller build\\MediaHub.spec --clean --noconfirm",
            "pause",
            "",
        ])
        (build / "build_exe.bat").write_text(exe_bat, encoding="utf-8")
        zip_bat = "\r\n".join([
            "@echo off",
            "cd /d %~dp0..",
            "python tools\\mediahub_selftest.py --mode release",
            "echo Release-Test beendet. Danach kann das Release-ZIP aus MediaHub erstellt werden.",
            "pause",
            "",
        ])
        (build / "build_zip.bat").write_text(zip_bat, encoding="utf-8")
        (build / "README_BUILD.txt").write_text(
            "MediaHub Build-Hinweise\n"
            "=======================\n\n"
            "1. build_exe.bat erstellt mit PyInstaller eine Windows-EXE.\n"
            "2. Vor dem finalen Release den Selbsttest im Release-Modus starten.\n"
            "3. Private Daten werden nicht in release_ready/ kopiert.\n"
            "4. Installer-Erstellung folgt im finalen Schritt nach erfolgreichem EXE-Test.\n",
            encoding="utf-8",
        )
        return {"ok": True, "message": "Build-Dateien erstellt.", "target": str(build)}

    def clean_runtime_preview(self):
        checks = []
        for rel in ("logs", "downloads", "downloads/work", "downloads/Fertig", "Backups", "__pycache__"):
            path = self.base_dir / rel
            if path.exists():
                count = sum(1 for _ in path.rglob("*")) if path.is_dir() else 1
                checks.append(f"{rel}: {count} Eintraege wuerden bereinigt/geleert")
            else:
                checks.append(f"{rel}: nicht vorhanden")
        return {"ok": True, "message": "Bereinigungs-Trockenlauf abgeschlossen.", "details": checks}

    def latest_report(self):
        html = self.logs_dir / "release_report_latest.html"
        txt = self.logs_dir / "release_report_latest.txt"
        return html if html.exists() else txt

    def _safe_version(self):
        return (self.app_version or "dev").replace("v", "").replace(".", "_").replace("-", "_")

    def _write_json(self, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _create_empty_database(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        conn = sqlite3.connect(path)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)", ("created_by", "MediaHub ReleaseService"))
            conn.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)", ("version", self.app_version))
            conn.commit()
        finally:
            conn.close()

    def _copy_tree_if_exists(self, src: Path, dst: Path, details, label):
        if not src.exists():
            return
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", "release_ready", "build", "dist")
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=ignore)
        details.append(f"{label} kopiert")

    def _write_reports(self, report, stamp):
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            "MediaHub Release Report", "=======================", f"Version: {report['version']}", f"Erstellt: {report['created']}", f"Ziel: {report['target']}", f"ZIP: {report.get('zip', '-')}", f"Status: {'OK' if report['ok'] else 'FEHLER'}", "",
            "Details:", *[f"[OK] {d}" for d in report.get("details", [])], "",
            "Warnungen:", *([f"[WARN] {w}" for w in report.get("warnings", [])] or ["keine"]), "",
            "Fehler:", *([f"[FEHLER] {e}" for e in report.get("errors", [])] or ["keine"]),
        ]
        txt = "\n".join(lines)
        for name in (f"release_report_{stamp}.txt", "release_report_latest.txt"):
            (self.logs_dir / name).write_text(txt, encoding="utf-8")
        html = "<html><body><pre>" + txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre></body></html>"
        for name in (f"release_report_{stamp}.html", "release_report_latest.html"):
            (self.logs_dir / name).write_text(html, encoding="utf-8")

    def _pyinstaller_spec(self):
        return """# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).parent
project = root.parent

a = Analysis(
    [str(project / 'main.py')],
    pathex=[str(project)],
    binaries=[],
    datas=[
        (str(project / 'config'), 'config'),
        (str(project / 'docs'), 'docs'),
        (str(project / 'plugins'), 'plugins'),
        (str(project / 'tools'), 'tools'),
        (str(project / 'assets'), 'assets'),
        (str(project / 'README.md'), '.'),
        (str(project / 'CHANGELOG.md'), '.'),
        (str(project / 'THIRD_PARTY_NOTICES.md'), '.'),
        (str(project / 'THIRD_PARTY_LICENSES.md'), '.'),
        (str(project / 'licenses'), 'licenses'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MediaHub', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, upx_exclude=[], name='MediaHub')
"""
