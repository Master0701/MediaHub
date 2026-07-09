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
        )

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
                zip_file.extractall(temp_dir)

            manifest_files = list(temp_dir.glob("*/plugin.json"))

            if not manifest_files:
                manifest_files = list(temp_dir.glob("plugin.json"))

            if not manifest_files:
                shutil.rmtree(temp_dir)
                return False, "Keine plugin.json im Plugin gefunden."

            manifest = manifest_files[0]
            plugin = self.load_manifest(manifest)

            if plugin is None:
                shutil.rmtree(temp_dir)
                return False, "plugin.json ist ungültig."

            target_dir = self.plugins_dir / plugin.plugin_id

            if target_dir.exists():
                shutil.rmtree(target_dir)

            if manifest.parent == temp_dir:
                shutil.copytree(temp_dir, target_dir)
            else:
                shutil.copytree(manifest.parent, target_dir)

            shutil.rmtree(temp_dir)

            return True, f"Plugin installiert: {plugin.name} v{plugin.version}"

        except Exception as error:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            return False, f"Plugin konnte nicht installiert werden:\n{error}"