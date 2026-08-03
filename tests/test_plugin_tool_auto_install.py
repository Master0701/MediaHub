from __future__ import annotations

import json
import zipfile
from pathlib import Path

from src.mediahub.plugins.plugin_loader import PluginLoader


def _write_plugin_package(
    target: Path,
    *,
    required_tools=None,
    optional_tools=None,
    auto_install=True,
) -> None:
    staging = target.parent / "package"
    plugin_dir = staging / "mediahub.test_tool_plugin"
    plugin_dir.mkdir(parents=True)

    manifest = {
        "id": "mediahub.test_tool_plugin",
        "name": "Test Tool Plugin",
        "version": "1.0.0",
        "enabled": True,
        "entry": "plugin.py",
        "required_tools": required_tools or [],
        "optional_tools": optional_tools or [],
        "install_declared_tools_on_plugin_install": auto_install,
    }
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        "class Plugin: pass\n",
        encoding="utf-8",
    )

    with zipfile.ZipFile(target, "w") as archive:
        for file in plugin_dir.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(staging))


def test_plugin_install_runs_declared_optional_tool(
    tmp_path: Path,
    monkeypatch,
):
    package = tmp_path / "plugin.mhplugin"
    _write_plugin_package(
        package,
        optional_tools=[{"id": "renamer", "required": False}],
    )

    installed = []

    class FakeToolService:
        def __init__(self, base_dir):
            self.base_dir = base_dir

        def find_tool_status(self, tool_id, include_version=False):
            return {
                "tool_id": tool_id,
                "display_name": "ReNamer Portable",
                "installed": False,
                "can_install": True,
            }

        def install_plugin_tool(self, tool_id):
            installed.append(tool_id)
            return {
                "tool_id": tool_id,
                "path": tmp_path / "tools" / "renamer" / "ReNamer.exe",
            }

    monkeypatch.setattr(
        "src.mediahub.services.tool_service.ToolService",
        FakeToolService,
    )

    loader = PluginLoader(tmp_path)
    success, message = loader.install_mhplugin(package)

    assert success is True
    assert installed == ["renamer"]
    assert "Tool eingerichtet: ReNamer Portable" in message


def test_optional_tool_failure_keeps_plugin_installed(
    tmp_path: Path,
    monkeypatch,
):
    package = tmp_path / "plugin.mhplugin"
    _write_plugin_package(
        package,
        optional_tools=[{"id": "renamer", "required": False}],
    )

    class FakeToolService:
        def __init__(self, base_dir):
            pass

        def find_tool_status(self, tool_id, include_version=False):
            return {
                "display_name": "ReNamer Portable",
                "installed": False,
                "can_install": True,
            }

        def install_plugin_tool(self, tool_id):
            raise RuntimeError("Download fehlgeschlagen")

    monkeypatch.setattr(
        "src.mediahub.services.tool_service.ToolService",
        FakeToolService,
    )

    loader = PluginLoader(tmp_path)
    success, message = loader.install_mhplugin(package)

    assert success is True
    assert "WARNUNG:" in message
    assert (
        tmp_path
        / "plugins"
        / "mediahub.test_tool_plugin"
        / "plugin.json"
    ).is_file()
