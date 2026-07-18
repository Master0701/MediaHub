from __future__ import annotations

from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import urllib.request
import urllib.parse
import zipfile
from datetime import datetime, timezone


class ToolService:
    """Zentrale Verwaltung der von MediaHub und Plugins verwendeten Werkzeuge."""

    CORE_TOOLS = {
        "yt-dlp": {
            "display_name": "yt-dlp",
            "folder": "yt-dlp",
            "exe": "yt-dlp.exe",
            "category": "mediahub",
            "license": "Unlicense",
            "homepage": "https://github.com/yt-dlp/yt-dlp",
            "release_api": "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
            "version_args": ["--version"],
            "first_line_only": False,
        },
        "ffmpeg": {
            "display_name": "FFmpeg",
            "folder": "ffmpeg",
            "exe": "ffmpeg.exe",
            "category": "mediahub",
            "license": "GPL/LGPL – abhängig vom verwendeten Build",
            "homepage": "https://ffmpeg.org/",
            "version_args": ["-version"],
            "first_line_only": True,
        },
        "ffprobe": {
            "display_name": "FFprobe",
            "folder": "ffmpeg",
            "exe": "ffprobe.exe",
            "category": "mediahub",
            "license": "GPL/LGPL – abhängig vom verwendeten Build",
            "homepage": "https://ffmpeg.org/",
            "version_args": ["-version"],
            "first_line_only": True,
        },
        "deno": {
            "display_name": "Deno",
            "folder": "deno",
            "exe": "deno.exe",
            "category": "mediahub",
            "license": "MIT",
            "homepage": "https://deno.com/",
            "release_api": "https://api.github.com/repos/denoland/deno/releases/latest",
            "version_args": ["--version"],
            "first_line_only": True,
        },
    }

    PLUGIN_TOOLS = {
        "mediainfo": {
            "display_name": "MediaInfo",
            "folder": "mediainfo",
            "exe": "mediainfo.exe",
            "category": "plugin",
            "license": "BSD-2-Clause",
            "homepage": "https://mediaarea.net/MediaInfo",
            # MediaInfo darf für die Statusanzeige nicht gestartet werden.
            # Auf Windows kann mediainfo.exe auch die GUI-Ausgabe sein; ein
            # Versionsaufruf würde dann beim Öffnen des Tool-Centers ein
            # zusätzliches MediaInfo-Fenster anzeigen.
            "version_args": [],
            "version_probe": False,
            "first_line_only": True,
            "release_api": "https://api.github.com/repos/MediaArea/MediaInfo/releases/latest",
            "asset_pattern": r"MediaInfo_CLI_.*_Windows_x64\.zip$",
            "install_kind": "github_zip",
            "search_names": ["mediainfo.exe", "MediaInfo.exe"],
        },
        "tesseract": {
            "display_name": "Tesseract OCR",
            "folder": "tesseract",
            "exe": "tesseract.exe",
            "category": "plugin",
            "license": "Apache-2.0",
            "homepage": "https://github.com/tesseract-ocr/tesseract",
            "version_args": ["--version"],
            "first_line_only": True,
            "download_page": "https://digi.bib.uni-mannheim.de/tesseract/",
            "asset_pattern": r"tesseract-ocr-w64-setup-[^\"']+\.exe",
            "install_kind": "portable_installer",
            "installer_args": ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"],
            "installer_dir_arg": "/DIR={path}",
            "search_names": ["tesseract.exe"],
        },
        "mkvtoolnix": {
            "display_name": "MKVToolNix",
            "folder": "mkvtoolnix",
            "exe": "mkvmerge.exe",
            "category": "plugin",
            "license": "GPL-2.0-or-later",
            "homepage": "https://mkvtoolnix.download/",
            "version_args": ["--version"],
            "first_line_only": True,
            "download_page": "https://mkvtoolnix.download/downloads.html",
            "asset_pattern": r"mkvtoolnix-64-bit-[0-9.]+-setup\.exe",
            "install_kind": "portable_installer",
            "installer_args": ["/S"],
            "installer_dir_arg": "/D={path}",
            "search_names": ["mkvmerge.exe"],
        },
    }

    YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    DENO_URL = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"

    FFMPEG_URLS = [
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    ]

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.tools_dir = self.base_dir / "tools"

        self.yt_dlp = self.tools_dir / "yt-dlp" / "yt-dlp.exe"
        self.ffmpeg = self.tools_dir / "ffmpeg" / "ffmpeg.exe"
        self.ffprobe = self.tools_dir / "ffmpeg" / "ffprobe.exe"
        self.deno = self.tools_dir / "deno" / "deno.exe"

        self._plugin_tool_usage: dict[str, dict[str, set[str]]] = {}
        self._change_listeners: list = []
        self._update_cache: dict[str, dict] = {}

    def ensure_tools_dir(self) -> None:
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        for definition in self.all_tool_definitions().values():
            (self.tools_dir / str(definition.get("folder") or "misc")).mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_tools()

    def _tool_folder(self, tool_id: str) -> Path:
        definition = self.tool_definition(tool_id)
        return self.tools_dir / str(definition.get("folder") or tool_id)

    def _preferred_tool_path(self, tool_id: str) -> Path:
        definition = self.tool_definition(tool_id)
        return self._tool_folder(tool_id) / str(definition["exe"])

    def _legacy_tool_path(self, tool_id: str) -> Path:
        definition = self.tool_definition(tool_id)
        return self.tools_dir / str(definition["exe"])

    def _manifest_path(self, tool_id: str) -> Path:
        return self._tool_folder(tool_id) / "manifest.json"

    def _write_manifest(self, tool_id: str, *, source_url: str = "", version: str = "") -> None:
        definition = self.tool_definition(tool_id)
        path = self._preferred_tool_path(tool_id)
        if not path.exists():
            return
        payload = {
            "schema_version": 1,
            "tool_id": tool_id,
            "name": definition.get("display_name", tool_id),
            "version": version or self._get_version(path, list(definition.get("version_args") or []), bool(definition.get("first_line_only", False))),
            "source_url": source_url,
            "homepage": definition.get("homepage", ""),
            "license": definition.get("license", "unbekannt"),
            "portable": True,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "executable": str(path.relative_to(self.tools_dir)),
        }
        self._manifest_path(tool_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _migrate_legacy_tools(self) -> None:
        """Übernimmt alte lose Tool-Dateien ohne bestehende Installationen zu brechen."""
        groups = {
            "yt-dlp": ["yt-dlp.exe"],
            "ffmpeg": ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"],
            "deno": ["deno.exe"],
            "mediainfo": ["mediainfo.exe", "MediaInfo.exe"],
            "tesseract": ["tesseract.exe"],
            "mkvtoolnix": ["mkvmerge.exe", "mkvpropedit.exe", "mkvinfo.exe", "mkvextract.exe"],
        }
        for tool_id, names in groups.items():
            folder = self._tool_folder(tool_id)
            migrated = False
            for name in names:
                legacy = self.tools_dir / name
                target = folder / name
                if legacy.exists() and not target.exists():
                    folder.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(legacy, target)
                    legacy.unlink(missing_ok=True)
                    migrated = True
            if migrated and self._preferred_tool_path(tool_id).exists():
                self._write_manifest(tool_id, source_url="legacy-migration")


    def add_change_listener(self, callback) -> None:
        """Registriert einen Listener für Änderungen an der Tool-Nutzung."""

        if callable(callback) and callback not in self._change_listeners:
            self._change_listeners.append(callback)

    def remove_change_listener(self, callback) -> None:
        """Entfernt einen zuvor registrierten Änderungs-Listener."""

        if callback in self._change_listeners:
            self._change_listeners.remove(callback)

    def _notify_changed(self) -> None:
        """Informiert registrierte Oberflächen über geänderte Tool-Daten."""

        for callback in list(self._change_listeners):
            try:
                callback()
            except Exception:
                # Eine geschlossene oder fehlerhafte Oberfläche darf die
                # Tool-Verwaltung nicht blockieren.
                continue

    def synchronize_plugin_tools(self, plugins) -> bool:
        """Übernimmt die Tool-Nutzung aller derzeit aktivierten Plugins.

        Die Daten werden als ein gemeinsamer Zustand ersetzt. Dadurch erhält
        der Tool-Manager genau eine Änderungsmeldung und deaktivierte oder
        entfernte Plugins verschwinden sofort aus der Nutzungsanzeige.
        """

        new_usage: dict[str, dict[str, set[str]]] = {}
        for plugin in plugins or []:
            if not bool(getattr(plugin, "enabled", False)):
                continue

            plugin_id = str(getattr(plugin, "plugin_id", "") or "").strip()
            if not plugin_id:
                continue

            required = {
                str(tool_id).strip().lower()
                for tool_id in (getattr(plugin, "required_tools", None) or [])
                if str(tool_id).strip().lower() in self.PLUGIN_TOOLS
            }
            optional = {
                str(tool_id).strip().lower()
                for tool_id in (getattr(plugin, "optional_tools", None) or [])
                if str(tool_id).strip().lower() in self.PLUGIN_TOOLS
            }
            optional.difference_update(required)
            new_usage[plugin_id] = {"required": required, "optional": optional}

        if new_usage == self._plugin_tool_usage:
            return False

        self._plugin_tool_usage = new_usage
        self._notify_changed()
        return True

    @classmethod
    def all_tool_definitions(cls) -> dict[str, dict]:
        """Liefert eine Kopie aller bekannten Werkzeugdefinitionen."""

        definitions: dict[str, dict] = {}
        for tool_id, definition in cls.CORE_TOOLS.items():
            definitions[tool_id] = dict(definition)
        for tool_id, definition in cls.PLUGIN_TOOLS.items():
            definitions[tool_id] = dict(definition)
        return definitions

    @classmethod
    def tool_definition(cls, tool_id: str) -> dict:
        """Liefert die Definition eines bekannten Werkzeugs."""

        normalized = str(tool_id or "").strip().lower()
        definition = cls.all_tool_definitions().get(normalized)
        if definition is None:
            raise KeyError(f"Unbekanntes Tool: {tool_id}")
        return definition

    def tool_path(self, tool_id: str) -> Path:
        """Liefert den portablen MediaHub-Pfad mit Rückfall auf alte lose Dateien."""

        normalized = str(tool_id or "").strip().lower()
        preferred = self._preferred_tool_path(normalized)
        if preferred.exists():
            return preferred
        legacy = self._legacy_tool_path(normalized)
        return legacy if legacy.exists() else preferred

    def missing_required_plugin_tools(self) -> list[str]:
        """Liefert fehlende Pflichttools aller aktivierten Plugins."""

        result = []
        for tool_id in sorted(self.PLUGIN_TOOLS):
            usage = self.get_tool_usage_without_status(tool_id)
            if usage["required_by"] and not self.tool_path(tool_id).exists():
                result.append(tool_id)
        return result

    def _github_release_asset(self, definition: dict) -> tuple[str, str]:
        request = urllib.request.Request(str(definition["release_api"]), headers={"User-Agent": "MediaHub", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        pattern = re.compile(str(definition.get("asset_pattern") or ".*"), re.IGNORECASE)
        for asset in payload.get("assets") or []:
            name = str(asset.get("name") or "")
            if pattern.search(name):
                return str(asset.get("browser_download_url") or ""), str(payload.get("tag_name") or payload.get("name") or "")
        raise RuntimeError(f"Kein passendes Windows-x64-Paket für {definition['display_name']} gefunden.")

    def _page_download_asset(self, definition: dict) -> str:
        page_url = str(definition["download_page"] or "")
        request = urllib.request.Request(page_url, headers={"User-Agent": "MediaHub"})
        with urllib.request.urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
        matches = re.findall(str(definition.get("asset_pattern") or ".*"), html, flags=re.IGNORECASE)
        if not matches:
            raise RuntimeError(f"Kein passendes Downloadpaket für {definition['display_name']} gefunden.")
        name = sorted(set(matches), key=self._version_key, reverse=True)[0]
        return urllib.parse.urljoin(page_url, name)

    def install_plugin_tool(self, tool_id: str, log_callback=None) -> dict:
        """Installiert ein Plugin-Werkzeug portabel unter MediaHub/tools."""

        normalized = str(tool_id or "").strip().lower()
        if normalized not in self.PLUGIN_TOOLS:
            raise KeyError(f"Unbekanntes Plugin-Tool: {tool_id}")
        definition = self.PLUGIN_TOOLS[normalized]
        target_folder = self._tool_folder(normalized)
        target_folder.mkdir(parents=True, exist_ok=True)
        stage = self.tools_dir / "temp" / normalized
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True, exist_ok=True)
        source_url = ""
        version = ""
        backup = self.tools_dir / "backups" / normalized
        shutil.rmtree(backup, ignore_errors=True)
        had_existing = target_folder.exists() and any(target_folder.iterdir())
        if had_existing:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target_folder, backup)
        try:
            kind = str(definition.get("install_kind") or "")
            if kind == "github_zip":
                source_url, version = self._github_release_asset(definition)
                archive = stage / "package.zip"
                if log_callback:
                    log_callback(f"Lade {definition['display_name']} portabel herunter …")
                self.download_file(source_url, archive, log_callback)
                if not zipfile.is_zipfile(archive):
                    raise RuntimeError("Das geladene Paket ist keine gültige ZIP-Datei.")
                extract = stage / "extract"
                with zipfile.ZipFile(archive, "r") as zf:
                    zf.extractall(extract)
                for item in extract.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(extract)
                        # Ein einzelner Verpackungsordner wird abgeflacht.
                        parts = rel.parts[1:] if len(rel.parts) > 1 else rel.parts
                        destination = target_folder.joinpath(*parts)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, destination)
            elif kind == "portable_installer":
                source_url = self._page_download_asset(definition)
                installer = stage / Path(urllib.parse.urlparse(source_url).path).name
                if log_callback:
                    log_callback(f"Lade {definition['display_name']} herunter …")
                self.download_file(source_url, installer, log_callback)
                if os.name != "nt":
                    raise RuntimeError("Die portable Windows-Installation kann nur unter Windows ausgeführt werden.")
                directory_arg = str(definition.get("installer_dir_arg") or "/D={path}").format(path=target_folder)
                args = [str(installer), *list(definition.get("installer_args") or ["/S"]), directory_arg]
                if log_callback:
                    log_callback(f"Entpacke {definition['display_name']} in den MediaHub-Toolordner …")
                result = subprocess.run(args, capture_output=True, text=True, timeout=900)
                if result.returncode != 0:
                    output = "\n".join(x for x in [result.stdout, result.stderr] if x).strip()
                    raise RuntimeError(output or f"Installer-Fehlercode {result.returncode}")
            else:
                raise RuntimeError(f"Für {definition['display_name']} ist keine portable Installationsquelle hinterlegt.")

            expected = self._preferred_tool_path(normalized)
            if not expected.exists():
                found = list(target_folder.rglob(str(definition["exe"])))
                if found:
                    shutil.copy2(found[0], expected)
            self._validate_tool_file(normalized, expected)
            self._write_manifest(normalized, source_url=source_url, version=version)
            self._update_cache.pop(normalized, None)
            self._notify_changed()
            if log_callback:
                log_callback(f"{definition['display_name']} wurde portabel eingerichtet.")
            shutil.rmtree(backup, ignore_errors=True)
            return self.get_tool_status(normalized, include_version=True)
        except Exception:
            if had_existing and backup.exists():
                shutil.rmtree(target_folder, ignore_errors=True)
                shutil.copytree(backup, target_folder)
            elif not had_existing:
                shutil.rmtree(target_folder, ignore_errors=True)
                target_folder.mkdir(parents=True, exist_ok=True)
            raise
        finally:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.rmtree(backup, ignore_errors=True)

    def install_missing_required_plugin_tools(self, log_callback=None) -> list[dict]:
        """Installiert ausschließlich fehlende Pflichttools aktivierter Plugins."""

        installed = []
        for tool_id in self.missing_required_plugin_tools():
            installed.append(self.install_plugin_tool(tool_id, log_callback=log_callback))
        return installed

    def install_missing_required_tools(self, log_callback=None) -> list[dict]:
        """Installiert alle fehlenden Pflichttools von MediaHub und aktivierten Plugins.

        Die vier MediaHub-Kernwerkzeuge werden über die vorhandenen offiziellen
        Downloadwege eingerichtet. Plugin-Pflichttools werden anschließend portabel im MediaHub-Toolordner installiert. Das Ergebnis enthält einen Eintrag je erfolgreich
        eingerichteter Tool-Gruppe bzw. je Plugin-Werkzeug.
        """

        installed: list[dict] = []
        missing_core = self.missing_tools()
        if missing_core:
            before = set(missing_core)
            self.download_missing_tools(log_callback=log_callback)
            after = set(self.missing_tools())
            completed = sorted(before - after)
            for filename in completed:
                tool_id = {
                    "yt-dlp.exe": "yt-dlp",
                    "ffmpeg.exe": "ffmpeg",
                    "ffprobe.exe": "ffprobe",
                    "deno.exe": "deno",
                }.get(filename)
                if tool_id:
                    installed.append(self.get_tool_status(tool_id, include_version=True))

        installed.extend(
            self.install_missing_required_plugin_tools(log_callback=log_callback)
        )
        return installed

    def plugin_tool_path(self, tool_id: str) -> Path:
        """Liefert den Pfad eines registrierten Plugin-Werkzeugs."""

        normalized = str(tool_id or "").strip().lower()
        if normalized not in self.PLUGIN_TOOLS:
            raise KeyError(f"Unbekanntes Plugin-Tool: {tool_id}")
        return self.tool_path(normalized)

    def register_plugin_tools(
        self,
        plugin_id: str,
        required_tools: list[str] | None = None,
        optional_tools: list[str] | None = None,
    ) -> None:
        """Registriert die Pflicht- und optionalen Werkzeuge eines Plugins."""

        normalized_plugin_id = str(plugin_id or "").strip()
        if not normalized_plugin_id:
            return

        required = {
            str(tool_id).strip().lower()
            for tool_id in (required_tools or [])
            if str(tool_id).strip().lower() in self.PLUGIN_TOOLS
        }
        optional = {
            str(tool_id).strip().lower()
            for tool_id in (optional_tools or [])
            if str(tool_id).strip().lower() in self.PLUGIN_TOOLS
        }
        optional.difference_update(required)

        new_value = {"required": required, "optional": optional}
        if self._plugin_tool_usage.get(normalized_plugin_id) != new_value:
            self._plugin_tool_usage[normalized_plugin_id] = new_value
            self._notify_changed()

    def unregister_plugin_tools(self, plugin_id: str) -> None:
        """Entfernt die Werkzeugzuordnung eines Plugins."""

        normalized_plugin_id = str(plugin_id or "").strip()
        if normalized_plugin_id and normalized_plugin_id in self._plugin_tool_usage:
            self._plugin_tool_usage.pop(normalized_plugin_id, None)
            self._notify_changed()

    def clear_plugin_tool_usage(self) -> None:
        """Entfernt alle registrierten Plugin-Werkzeugzuordnungen."""

        if self._plugin_tool_usage:
            self._plugin_tool_usage.clear()
            self._notify_changed()

    def get_tool_usage(self, tool_id: str) -> dict:
        """Liefert die Plugin-Nutzung eines registrierten Plugin-Werkzeugs."""

        normalized = str(tool_id or "").strip().lower()
        if normalized not in self.PLUGIN_TOOLS:
            raise KeyError(f"Unbekanntes Plugin-Tool: {tool_id}")

        required_by: list[str] = []
        optional_by: list[str] = []

        for plugin_id, usage in self._plugin_tool_usage.items():
            if normalized in usage.get("required", set()):
                required_by.append(plugin_id)
            elif normalized in usage.get("optional", set()):
                optional_by.append(plugin_id)

        status = self.get_tool_status(normalized, include_version=False)
        return {
            "tool_id": normalized,
            "display_name": status["display_name"],
            "path": status["path"],
            "installed": status["installed"],
            "required_by": sorted(required_by),
            "optional_by": sorted(optional_by),
        }

    def get_all_plugin_tool_usage(self) -> list[dict]:
        """Liefert die Nutzungsübersicht aller Plugin-Werkzeuge."""

        return [self.get_tool_usage(tool_id) for tool_id in sorted(self.PLUGIN_TOOLS)]

    def get_tool_status(self, tool_id: str, include_version: bool = True) -> dict:
        """Liefert einen einheitlichen Statusdatensatz für ein Werkzeug."""

        normalized = str(tool_id or "").strip().lower()
        definition = self.tool_definition(normalized)
        path = self.tool_path(normalized)
        installed = path.exists()

        required_by: list[str] = []
        optional_by: list[str] = []

        if normalized in self.PLUGIN_TOOLS:
            usage = self.get_tool_usage_without_status(normalized)
            required_by = usage["required_by"]
            optional_by = usage["optional_by"]

        used_by = ["MediaHub"] if normalized in self.CORE_TOOLS else []
        used_by.extend(required_by)
        used_by.extend(plugin_id for plugin_id in optional_by if plugin_id not in used_by)

        version = "nicht geprüft"
        if include_version:
            if not installed:
                version = "fehlt"
            elif definition.get("version_probe", True) is False:
                version = "installiert (Version nicht automatisch geprüft)"
            else:
                version = self._get_version(
                    path,
                    list(definition.get("version_args") or []),
                    first_line_only=bool(definition.get("first_line_only", False)),
                )

        installation_source = self._installation_source(normalized, path, installed)
        can_install = bool(normalized in self.PLUGIN_TOOLS and definition.get("install_kind"))
        safe_mediahub_update = normalized in {"yt-dlp", "deno"}
        portable_update = bool(can_install)
        update_method = "mediahub_safe" if safe_mediahub_update else ("portable" if portable_update else "manual")
        update_info = dict(self._update_cache.get(normalized) or {})
        latest_version = str(update_info.get("latest_version") or "noch nicht geprüft")
        update_available = update_info.get("update_available")
        update_status = str(update_info.get("update_status") or ("Noch nicht geprüft" if installed else "Nicht installiert"))

        return {
            "tool_id": normalized,
            "display_name": str(definition.get("display_name") or normalized),
            "category": str(definition.get("category") or "plugin"),
            "path": path,
            "executable": str(definition.get("exe") or ""),
            "installed": installed,
            "version": version,
            "latest_version": latest_version,
            "update_available": update_available,
            "update_status": update_status,
            "installation_source": installation_source,
            "can_install": can_install,
            "can_reinstall": bool(installed and (safe_mediahub_update or can_install)),
            "can_update": bool(installed and (safe_mediahub_update or can_install)),
            "safe_update_supported": bool(safe_mediahub_update or portable_update),
            "update_method": update_method,
            "license": str(definition.get("license") or "unbekannt"),
            "homepage": str(definition.get("homepage") or ""),
            "required_by": required_by,
            "optional_by": optional_by,
            "used_by": used_by,
            "is_required": bool(normalized in self.CORE_TOOLS or required_by),
            "is_optional": bool(optional_by and normalized not in self.CORE_TOOLS and not required_by),
            "is_unused": bool(normalized in self.PLUGIN_TOOLS and not required_by and not optional_by),
        }


    @staticmethod
    def _version_key(value: str) -> tuple[int, ...]:
        numbers = re.findall(r"\d+", str(value or ""))
        return tuple(int(number) for number in numbers[:4])

    def _github_latest_version(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MediaHub",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("tag_name") or payload.get("name") or "").strip()

    def _winget_latest_version(self, winget_id: str) -> str:
        winget = shutil.which("winget")
        if not winget:
            raise RuntimeError("Windows Package Manager (winget) wurde nicht gefunden.")
        result = subprocess.run(
            [winget, "show", "--id", winget_id, "--exact", "--accept-source-agreements", "--disable-interactivity"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = "\n".join(part for part in [result.stdout, result.stderr] if part)
        if result.returncode != 0:
            raise RuntimeError(output.strip() or f"WinGet wurde mit Fehlercode {result.returncode} beendet.")
        for line in output.splitlines():
            match = re.match(r"\s*(Version|Versionen)\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
            if match:
                return match.group(2).strip()
        raise RuntimeError("Die verfügbare Version konnte aus der WinGet-Ausgabe nicht gelesen werden.")

    def check_tool_update(self, tool_id: str) -> dict:
        """Prüft die neueste Version, ohne ein Update zu installieren."""

        normalized = str(tool_id or "").strip().lower()
        definition = self.tool_definition(normalized)
        status = self.get_tool_status(normalized, include_version=True)
        if not status["installed"]:
            result = {
                "latest_version": "nicht geprüft",
                "update_available": None,
                "update_status": "Nicht installiert",
            }
            self._update_cache[normalized] = result
            return {**status, **result}

        try:
            if definition.get("release_api"):
                latest = self._github_latest_version(str(definition["release_api"]))
            elif definition.get("download_page"):
                latest = Path(urllib.parse.urlparse(self._page_download_asset(definition)).path).name
            else:
                result = {
                    "latest_version": "nicht automatisch prüfbar",
                    "update_available": None,
                    "update_status": "Manuelle Prüfung erforderlich",
                }
                self._update_cache[normalized] = result
                return {**status, **result}

            installed_key = self._version_key(str(status.get("version") or ""))
            latest_key = self._version_key(latest)
            available = bool(installed_key and latest_key and latest_key > installed_key)
            result = {
                "latest_version": latest or "unbekannt",
                "update_available": available,
                "update_status": "Update verfügbar" if available else "Aktuell",
            }
        except Exception as error:
            result = {
                "latest_version": "Prüfung fehlgeschlagen",
                "update_available": None,
                "update_status": f"Fehler: {error}",
            }

        self._update_cache[normalized] = result
        self._notify_changed()
        return {**status, **result}

    def check_all_tool_updates(self) -> list[dict]:
        """Prüft alle installierten Tools nacheinander auf Updates."""

        results = []
        for tool_id in self.all_tool_definitions():
            if self.tool_path(tool_id).exists():
                results.append(self.check_tool_update(tool_id))
        return results

    def get_tool_assistant_status(self, include_versions: bool = True) -> dict:
        """Liefert den kompakten Gesamtzustand für den Tool-Assistenten."""

        data = self.get_tool_manager_data(include_versions=include_versions)
        tools = list(data.get("tools") or [])
        updates = [item for item in tools if item.get("update_available") is True]
        safe_updates = [
            item for item in updates
            if item.get("safe_update_supported") is True
        ]
        missing_required = [
            item for item in tools
            if not item.get("installed") and item.get("is_required")
        ]
        return {
            **data,
            "updates_available": len(updates),
            "safe_updates_available": len(safe_updates),
            "missing_required": len(missing_required),
            "safe_update_tools": safe_updates,
            "missing_required_tools": missing_required,
        }

    def update_all_available_safe_tools(self, log_callback=None) -> list[dict]:
        """Aktualisiert alle bereits geprüften, sicher unterstützten Tools."""

        results: list[dict] = []
        for tool_id in self.all_tool_definitions():
            status = self.find_tool_status(tool_id, include_version=False) or {}
            if status.get("safe_update_supported") is not True:
                continue
            if status.get("update_available") is not True:
                continue
            if log_callback:
                log_callback(f"Aktualisiere {status.get('display_name', tool_id)} …")
            try:
                updated = self.update_mediahub_tool(tool_id)
                results.append({
                    "tool_id": tool_id,
                    "display_name": status.get("display_name", tool_id),
                    "success": True,
                    "version": updated.get("version", "unbekannt"),
                })
                if log_callback:
                    log_callback(f"{status.get('display_name', tool_id)} wurde aktualisiert.")
            except Exception as error:
                results.append({
                    "tool_id": tool_id,
                    "display_name": status.get("display_name", tool_id),
                    "success": False,
                    "error": str(error),
                })
                if log_callback:
                    log_callback(f"Fehler bei {status.get('display_name', tool_id)}: {error}")
        return results

    def check_and_update_safe_tools(self, log_callback=None) -> dict:
        """Prüft alle Tools und aktualisiert danach sichere Updates gesammelt."""

        checked = self.check_all_tool_updates()
        updated = self.update_all_available_safe_tools(log_callback=log_callback)
        return {"checked": checked, "updated": updated}

    def _installation_source(self, tool_id: str, path: Path, installed: bool) -> str:
        """Ermittelt die Quelle ohne Programme oder Paketmanager zu starten."""

        if not installed:
            return "Nicht installiert"
        try:
            path.resolve().relative_to(self.tools_dir.resolve())
            return "MediaHub-Toolordner (portabel)"
        except (OSError, ValueError):
            return "Außerhalb des MediaHub-Toolordners"

    def get_tool_usage_without_status(self, tool_id: str) -> dict[str, list[str]]:
        """Interne Nutzungsauswertung ohne rekursiven Statusaufruf."""

        required_by: list[str] = []
        optional_by: list[str] = []

        for plugin_id, usage in self._plugin_tool_usage.items():
            if tool_id in usage.get("required", set()):
                required_by.append(plugin_id)
            elif tool_id in usage.get("optional", set()):
                optional_by.append(plugin_id)

        return {
            "required_by": sorted(required_by),
            "optional_by": sorted(optional_by),
        }

    def get_all_tool_statuses(self, include_versions: bool = True) -> list[dict]:
        """Liefert Hauptprogramm- und Plugin-Werkzeuge in einer gemeinsamen Liste."""

        return [
            self.get_tool_status(tool_id, include_version=include_versions)
            for tool_id in self.all_tool_definitions()
        ]

    def get_tool_summary(self, include_versions: bool = False) -> dict:
        """Liefert Zähler für die spätere Tool-Manager-Anzeige."""

        statuses = self.get_all_tool_statuses(include_versions=include_versions)
        return self._build_tool_summary(statuses)

    def get_tool_manager_data(
        self,
        include_versions: bool = True,
        category: str | None = None,
        state: str | None = None,
    ) -> dict:
        """Liefert die vollständige, filterbare Datenbasis für den Tool-Manager.

        Unterstützte Kategorien: ``all``, ``mediahub`` und ``plugin``.
        Unterstützte Statusfilter: ``all``, ``installed``, ``missing``,
        ``used``, ``unused``, ``required`` und ``optional``.
        """

        normalized_category = str(category or "all").strip().lower()
        normalized_state = str(state or "all").strip().lower()

        valid_categories = {"all", "mediahub", "plugin"}
        valid_states = {
            "all",
            "installed",
            "missing",
            "used",
            "unused",
            "required",
            "optional",
        }

        if normalized_category not in valid_categories:
            raise ValueError(f"Unbekannte Tool-Kategorie: {category}")
        if normalized_state not in valid_states:
            raise ValueError(f"Unbekannter Tool-Statusfilter: {state}")

        all_statuses = self.get_all_tool_statuses(include_versions=include_versions)
        filtered: list[dict] = []

        for status in all_statuses:
            if normalized_category != "all" and status["category"] != normalized_category:
                continue

            if normalized_state == "installed" and not status["installed"]:
                continue
            if normalized_state == "missing" and status["installed"]:
                continue
            if normalized_state == "used" and not status["used_by"]:
                continue
            if normalized_state == "unused" and not status["is_unused"]:
                continue
            if normalized_state == "required" and not status["is_required"]:
                continue
            if normalized_state == "optional" and not status["is_optional"]:
                continue

            filtered.append(status)

        filtered.sort(
            key=lambda item: (
                0 if item["category"] == "mediahub" else 1,
                item["display_name"].casefold(),
            )
        )

        return {
            "filters": {
                "category": normalized_category,
                "state": normalized_state,
            },
            "summary": self._build_tool_summary(all_statuses),
            "filtered_summary": self._build_tool_summary(filtered),
            "tools": filtered,
        }

    def find_tool_status(self, tool_id: str, include_version: bool = True) -> dict | None:
        """Liefert einen Tool-Status oder ``None`` bei unbekannter Kennung."""

        normalized = str(tool_id or "").strip().lower()
        if normalized not in self.all_tool_definitions():
            return None
        return self.get_tool_status(normalized, include_version=include_version)

    def get_tools_used_by(self, consumer_id: str, include_versions: bool = False) -> list[dict]:
        """Liefert alle Werkzeuge, die MediaHub oder ein Plugin verwendet."""

        normalized_consumer = str(consumer_id or "").strip()
        if not normalized_consumer:
            return []

        statuses = self.get_all_tool_statuses(include_versions=include_versions)
        result = [
            status
            for status in statuses
            if normalized_consumer in status["used_by"]
        ]
        return sorted(result, key=lambda item: item["display_name"].casefold())

    @staticmethod
    def _build_tool_summary(statuses: list[dict]) -> dict:
        """Erzeugt konsistente Zähler für eine beliebige Tool-Liste."""

        return {
            "total": len(statuses),
            "installed": sum(1 for item in statuses if item["installed"]),
            "missing": sum(1 for item in statuses if not item["installed"]),
            "required": sum(1 for item in statuses if item["is_required"]),
            "optional": sum(1 for item in statuses if item["is_optional"]),
            "unused": sum(1 for item in statuses if item["is_unused"]),
            "used": sum(1 for item in statuses if item["used_by"]),
        }

    def check_tools(self) -> dict:
        self.ensure_tools_dir()
        return {
            "yt-dlp.exe": self.yt_dlp.exists(),
            "ffmpeg.exe": self.ffmpeg.exists(),
            "ffprobe.exe": self.ffprobe.exists(),
            "deno.exe": self.deno.exists(),
        }

    def missing_tools(self) -> list[str]:
        return [name for name, exists in self.check_tools().items() if not exists]

    def ffmpeg_location(self) -> str:
        return str(self.ffmpeg.parent)

    def open_tools_folder(self) -> None:
        self.ensure_tools_dir()
        os.startfile(self.tools_dir)

    def get_tool_versions(self) -> dict:
        return {
            "yt-dlp": self._get_version(self.yt_dlp, ["--version"]),
            "ffmpeg": self._get_version(self.ffmpeg, ["-version"], first_line_only=True),
            "ffprobe": self._get_version(self.ffprobe, ["-version"], first_line_only=True),
            "deno": self._get_version(self.deno, ["--version"], first_line_only=True),
        }

    def _get_version(self, exe_path: Path, args: list[str], first_line_only: bool = False) -> str:
        if not exe_path.exists():
            return "fehlt"

        try:
            result = subprocess.run(
                [str(exe_path), *args],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = (result.stdout or result.stderr).strip()
            if first_line_only and output:
                return output.splitlines()[0]
            return output or "unbekannt"
        except Exception as error:
            return f"Fehler: {error}"

    def _validate_tool_file(self, tool_id: str, path: Path) -> None:
        """Prüft eine neue Tool-Datei vor dem endgültigen Austausch."""

        if not path.exists() or path.stat().st_size <= 0:
            raise RuntimeError(f"Die neue Datei für {tool_id} fehlt oder ist leer.")

        definition = self.tool_definition(tool_id)
        if definition.get("version_probe", True) is False:
            return

        version = self._get_version(
            path,
            list(definition.get("version_args") or []),
            first_line_only=bool(definition.get("first_line_only", False)),
        )
        if not version or version == "unbekannt" or str(version).startswith("Fehler:"):
            raise RuntimeError(f"Die neue Datei für {definition['display_name']} konnte nicht geprüft werden: {version}")

    def _safe_replace_tool_files(self, replacements: dict[Path, Path], validator=None) -> None:
        """Tauscht Tool-Dateien atomar aus und stellt sie bei Fehlern wieder her."""

        self.ensure_tools_dir()
        backup_dir = self.tools_dir / "_update_backup"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        backups: dict[Path, Path] = {}
        try:
            for target, staged in replacements.items():
                if not staged.exists():
                    raise RuntimeError(f"Vorbereitete Update-Datei fehlt: {staged.name}")
                if target.exists():
                    backup = backup_dir / target.name
                    shutil.copy2(target, backup)
                    backups[target] = backup

            for target, staged in replacements.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                temp_target = target.with_suffix(target.suffix + ".new")
                shutil.copy2(staged, temp_target)
                os.replace(temp_target, target)

            if callable(validator):
                validator()
        except Exception:
            for target in replacements:
                target.unlink(missing_ok=True)
                backup = backups.get(target)
                if backup and backup.exists():
                    shutil.copy2(backup, target)
            raise
        finally:
            shutil.rmtree(backup_dir, ignore_errors=True)

    def update_mediahub_tool(self, tool_id: str, log_callback=None) -> dict:
        """Aktualisiert ein MediaHub-Tool mit Backup und automatischem Rollback."""

        normalized = str(tool_id or "").strip().lower()
        if normalized in self.PLUGIN_TOOLS:
            return self.install_plugin_tool(normalized, log_callback=log_callback)
        if normalized not in {"yt-dlp", "deno"}:
            raise RuntimeError("Für dieses Tool ist der sichere Einzel-Updater noch nicht freigeschaltet.")

        self.ensure_tools_dir()
        stage_dir = self.tools_dir / "_update_stage" / normalized
        shutil.rmtree(stage_dir, ignore_errors=True)
        stage_dir.mkdir(parents=True, exist_ok=True)

        try:
            if normalized == "yt-dlp":
                staged = stage_dir / "yt-dlp.exe"
                self.download_file(self.YT_DLP_URL, staged, log_callback)
                self._validate_tool_file(normalized, staged)
                self._safe_replace_tool_files(
                    {self.yt_dlp: staged},
                    validator=lambda: self._validate_tool_file(normalized, self.yt_dlp),
                )
            else:
                archive = stage_dir / "deno.zip"
                extract_dir = stage_dir / "extract"
                self.download_file(self.DENO_URL, archive, log_callback)
                if not zipfile.is_zipfile(archive):
                    raise RuntimeError("Deno-Datei ist keine gültige ZIP-Datei.")
                with zipfile.ZipFile(archive, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
                found = list(extract_dir.rglob("deno.exe"))
                if not found:
                    raise RuntimeError("deno.exe wurde im Update-Paket nicht gefunden.")
                staged = found[0]
                self._validate_tool_file(normalized, staged)
                self._safe_replace_tool_files(
                    {self.deno: staged},
                    validator=lambda: self._validate_tool_file(normalized, self.deno),
                )

            self._write_manifest(normalized, source_url=self.YT_DLP_URL if normalized == "yt-dlp" else self.DENO_URL)
            self._update_cache.pop(normalized, None)
            self._notify_changed()
            return self.get_tool_status(normalized, include_version=True)
        finally:
            shutil.rmtree(stage_dir, ignore_errors=True)

    def download_file(self, url: str, target: Path, log_callback=None, timeout: int = 300) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        part_file = target.with_suffix(target.suffix + ".part")
        if part_file.exists():
            part_file.unlink()

        request = urllib.request.Request(url, headers={"User-Agent": "MediaHub"})
        if log_callback:
            log_callback(f"Download: {url}")

        with urllib.request.urlopen(request, timeout=timeout) as response:
            with part_file.open("wb") as file:
                shutil.copyfileobj(response, file)

        if target.exists():
            target.unlink()
        part_file.rename(target)

    def download_missing_tools(self, log_callback=None) -> None:
        self.ensure_tools_dir()
        missing = self.missing_tools()

        if not missing:
            if log_callback:
                log_callback("Alle Tools sind bereits vorhanden.")
            return

        if "yt-dlp.exe" in missing:
            if log_callback:
                log_callback("Lade yt-dlp.exe herunter...")
            self.yt_dlp.parent.mkdir(parents=True, exist_ok=True)
            self.download_file(self.YT_DLP_URL, self.yt_dlp, log_callback)
            self._write_manifest("yt-dlp", source_url=self.YT_DLP_URL)

        if "ffmpeg.exe" in missing or "ffprobe.exe" in missing:
            self.download_ffmpeg(log_callback)

        if "deno.exe" in missing:
            self.download_deno(log_callback)

        if log_callback:
            log_callback("Tool-Download abgeschlossen.")

    def redownload_all_tools(self, log_callback=None) -> None:
        self.ensure_tools_dir()
        for file in [self.yt_dlp, self.ffmpeg, self.ffprobe, self._tool_folder("ffmpeg") / "ffplay.exe", self.deno]:
            if file.exists():
                file.unlink()
        self.download_missing_tools(log_callback)

    def deno_path(self) -> str | None:
        if self.deno.exists():
            return str(self.deno)
        return None

    def download_deno(self, log_callback=None) -> None:
        zip_path = self.tools_dir / "downloads" / "deno.zip"
        extract_dir = self.tools_dir / "temp" / "deno_extract"

        if zip_path.exists():
            zip_path.unlink()
        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_dir.mkdir(parents=True, exist_ok=True)
        if log_callback:
            log_callback("Lade Deno herunter...")

        self.download_file(self.DENO_URL, zip_path, log_callback)
        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError("Deno-Datei ist keine gültige ZIP-Datei.")

        if log_callback:
            log_callback("Entpacke Deno...")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        found = list(extract_dir.rglob("deno.exe"))
        if not found:
            raise RuntimeError("deno.exe wurde nach dem Entpacken nicht gefunden.")

        shutil.copy2(found[0], self.deno)
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)

        self._write_manifest("deno", source_url=self.DENO_URL)
        if log_callback:
            log_callback("deno.exe eingerichtet.")

    def download_ffmpeg(self, log_callback=None) -> None:
        zip_path = self.tools_dir / "downloads" / "ffmpeg.zip"
        last_error = None

        for url in self.FFMPEG_URLS:
            try:
                if zip_path.exists():
                    zip_path.unlink()
                if log_callback:
                    log_callback("Lade FFmpeg herunter...")

                self.download_file(url, zip_path, log_callback)
                if not zipfile.is_zipfile(zip_path):
                    raise RuntimeError("FFmpeg-Datei ist keine gültige ZIP-Datei.")

                self.extract_ffmpeg(zip_path, log_callback)
                if self.ffmpeg.exists() and self.ffprobe.exists():
                    if log_callback:
                        log_callback("FFmpeg erfolgreich eingerichtet.")
                    return

                raise RuntimeError("ffmpeg.exe oder ffprobe.exe wurde nach dem Entpacken nicht gefunden.")
            except Exception as error:
                last_error = error
                if log_callback:
                    log_callback(f"FFmpeg-Quelle fehlgeschlagen: {error}")
                if zip_path.exists():
                    zip_path.unlink()

        raise RuntimeError(f"FFmpeg konnte nicht heruntergeladen werden: {last_error}")

    def extract_ffmpeg(self, zip_path: Path, log_callback=None) -> None:
        extract_dir = self.tools_dir / "temp" / "ffmpeg_extract"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_dir.mkdir(parents=True, exist_ok=True)
        if log_callback:
            log_callback("Entpacke FFmpeg...")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        for file_name in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
            found = list(extract_dir.rglob(file_name))
            if found:
                shutil.copy2(found[0], self._tool_folder("ffmpeg") / file_name)
                if log_callback:
                    log_callback(f"{file_name} eingerichtet.")

        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)
