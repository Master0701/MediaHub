from __future__ import annotations

import importlib.util
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from src.mediahub.plugins.plugin_api import MediaHubPluginAPI, PluginInfo


@dataclass
class RunningPlugin:
    info: PluginInfo
    module: ModuleType
    instance: Any


class PluginRuntime:
    def __init__(self, mediahub_api: MediaHubPluginAPI):
        self.mediahub_api = mediahub_api
        self._running: dict[str, RunningPlugin] = {}

    def is_running(self, plugin_id: str) -> bool:
        return plugin_id in self._running

    def start(self, plugin: PluginInfo) -> tuple[bool, str]:
        if self.is_running(plugin.plugin_id):
            return True, f"Plugin läuft bereits: {plugin.name}"
        if not plugin.enabled:
            return False, "Das Plugin ist im Manifest deaktiviert."
        if not plugin.entry:
            return False, "Kein Entry-Point eingetragen."

        entry_path = (plugin.path / plugin.entry).resolve()
        plugin_root = plugin.path.resolve()
        if plugin_root not in entry_path.parents or not entry_path.is_file():
            return False, f"Ungültiger Entry-Point: {plugin.entry}"

        shared_dir = plugin.path / "shared"
        inserted_paths: list[str] = []
        for path in (shared_dir, plugin.path):
            if path.exists():
                value = str(path)
                if value not in sys.path:
                    sys.path.insert(0, value)
                    inserted_paths.append(value)

        module_name = "mediahub_external_" + plugin.plugin_id.replace(".", "_").replace("-", "_")
        try:
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            if spec is None or spec.loader is None:
                return False, "Plugin-Modul konnte nicht vorbereitet werden."
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            plugin_class = self._find_plugin_class(module, plugin.class_name)
            if plugin_class is None:
                return False, "Keine passende Plugin-Klasse gefunden."

            instance = self._create_instance(plugin_class, plugin.path)
            start_method = getattr(instance, "start", None)
            if not callable(start_method):
                return False, "Das Plugin besitzt keine start()-Methode."
            start_method()

            self._running[plugin.plugin_id] = RunningPlugin(plugin, module, instance)
            self.mediahub_api.log(f"Gestartet: {plugin.name} v{plugin.version}")
            return True, f"Plugin gestartet: {plugin.name}"
        except Exception as error:
            sys.modules.pop(module_name, None)
            return False, f"Plugin konnte nicht gestartet werden:\n{error}"
        finally:
            for value in inserted_paths:
                try:
                    sys.path.remove(value)
                except ValueError:
                    pass

    def _find_plugin_class(self, module: ModuleType, class_name: str):
        if class_name:
            value = getattr(module, class_name, None)
            return value if inspect.isclass(value) else None
        for _, value in inspect.getmembers(module, inspect.isclass):
            if value.__module__ == module.__name__ and callable(getattr(value, "start", None)):
                return value
        return None

    def _create_instance(self, plugin_class, plugin_path: Path):
        signature = inspect.signature(plugin_class)
        kwargs = {}
        if "plugin_path" in signature.parameters:
            kwargs["plugin_path"] = plugin_path
        if "mediahub_api" in signature.parameters:
            kwargs["mediahub_api"] = self.mediahub_api
        return plugin_class(**kwargs)

    def stop(self, plugin_id: str) -> tuple[bool, str]:
        running = self._running.get(plugin_id)
        if running is None:
            return True, "Plugin läuft nicht."
        try:
            stop_method = getattr(running.instance, "stop", None)
            if callable(stop_method):
                stop_method()
            self._running.pop(plugin_id, None)
            sys.modules.pop(running.module.__name__, None)
            self.mediahub_api.log(f"Gestoppt: {running.info.name}")
            return True, f"Plugin gestoppt: {running.info.name}"
        except Exception as error:
            return False, f"Plugin konnte nicht gestoppt werden:\n{error}"

    def stop_all(self) -> None:
        for plugin_id in list(self._running):
            self.stop(plugin_id)
