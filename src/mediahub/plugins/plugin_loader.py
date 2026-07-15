from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from src.mediahub.plugins.plugin_api import PluginInfo


class PluginLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.plugins_dir = self.base_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def discover(self) -> list[PluginInfo]:
        plugins: list[PluginInfo] = []
        for manifest in sorted(self.plugins_dir.glob("*/plugin.json")):
            plugin = self.load_manifest(manifest)
            if plugin is not None:
                plugins.append(plugin)
        return plugins

    def load_manifest(self, manifest: Path) -> PluginInfo | None:
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            return None

        plugin_id = str(data.get("id") or manifest.parent.name).strip()
        if not plugin_id:
            return None

        permissions = data.get("permissions") or []
        if not isinstance(permissions, list):
            permissions = []

        ui = data.get("ui") or {}
        if not isinstance(ui, dict):
            ui = {}
        has_gui = bool(ui.get("enabled", data.get("has_gui", data.get("type") == "web")))
        ui_type = str(ui.get("type") or ("web" if data.get("type") == "web" else "native"))
        try:
            ui_order = int(ui.get("order", 100))
        except (TypeError, ValueError):
            ui_order = 100
        web_ui = ui.get("web") or {}
        if not isinstance(web_ui, dict):
            web_ui = {}
        try:
            web_ui_order = int(web_ui.get("order", ui_order))
        except (TypeError, ValueError):
            web_ui_order = ui_order

        return PluginInfo(
            plugin_id=plugin_id,
            name=str(data.get("name") or plugin_id),
            version=str(data.get("version") or "0.1.0"),
            author=str(data.get("author") or "Unbekannt"),
            description=str(data.get("description") or ""),
            plugin_type=str(data.get("type") or "tool"),
            enabled=bool(data.get("enabled", True)),
            path=manifest.parent,
            entry=str(data.get("entry") or ""),
            icon=str(data.get("icon") or ""),
            safe_mode=bool(data.get("safe_mode", True)),
            class_name=str(data.get("class_name") or ""),
            minimum_mediahub_version=str(data.get("minimum_mediahub_version") or ""),
            permissions=[str(item) for item in permissions],
            has_gui=has_gui,
            ui_type=ui_type,
            ui_title=str(ui.get("title") or data.get("gui_name") or data.get("name") or plugin_id),
            ui_route=str(ui.get("route") or data.get("gui_route") or ""),
            ui_icon=str(ui.get("icon") or data.get("gui_icon") or "🧩"),
            ui_order=ui_order,
            has_settings=bool(data.get("has_settings", False)),
            web_ui_enabled=bool(web_ui.get("enabled", False)),
            web_ui_title=str(web_ui.get("title") or ui.get("title") or data.get("name") or plugin_id),
            web_ui_route=str(web_ui.get("route") or ui.get("route") or ""),
            web_ui_icon=str(web_ui.get("icon") or ui.get("icon") or "🧩"),
            web_ui_order=web_ui_order,
            web_ui_shell=bool(web_ui.get("shell", False)),
        )

    def _safe_extract(self, archive: zipfile.ZipFile, target: Path) -> None:
        target_resolved = target.resolve()
        for member in archive.infolist():
            destination = (target / member.filename).resolve()
            if destination != target_resolved and target_resolved not in destination.parents:
                raise ValueError(f"Unsicherer Pfad im Plugin-Paket: {member.filename}")
        archive.extractall(target)

    def install_mhplugin(self, file_path: Path) -> tuple[bool, str]:
        file_path = Path(file_path)
        if not file_path.exists():
            return False, "Plugin-Datei wurde nicht gefunden."
        if file_path.suffix.lower() != ".mhplugin":
            return False, "Nur .mhplugin-Dateien werden unterstützt."

        temp_dir = self.plugins_dir / "_install_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(file_path, "r") as zip_file:
                self._safe_extract(zip_file, temp_dir)

            manifest_files = list(temp_dir.glob("*/plugin.json")) or list(temp_dir.glob("plugin.json"))
            if not manifest_files:
                return False, "Keine plugin.json im Plugin gefunden."

            manifest = manifest_files[0]
            plugin = self.load_manifest(manifest)
            if plugin is None:
                return False, "plugin.json ist ungültig."
            if not plugin.entry:
                return False, "Das Plugin enthält keinen Entry-Point."

            entry_file = manifest.parent / plugin.entry
            if not entry_file.is_file():
                return False, f"Entry-Datei fehlt: {plugin.entry}"

            target_dir = self.plugins_dir / plugin.plugin_id
            if target_dir.exists():
                shutil.rmtree(target_dir)

            source_dir = temp_dir if manifest.parent == temp_dir else manifest.parent
            shutil.copytree(source_dir, target_dir)
            return True, f"Plugin installiert: {plugin.name} v{plugin.version}"
        except Exception as error:
            return False, f"Plugin konnte nicht installiert werden:\n{error}"
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def uninstall(self, plugin: PluginInfo) -> tuple[bool, str]:
        try:
            if plugin.path.exists():
                shutil.rmtree(plugin.path)
            return True, f"Plugin entfernt: {plugin.name}"
        except Exception as error:
            return False, f"Plugin konnte nicht entfernt werden:\n{error}"
