from pathlib import Path

import pytest

from src.mediahub.services.tool_service import ToolService


def test_tool_manager_data_contains_all_known_tools(tmp_path: Path):
    service = ToolService(tmp_path)

    data = service.get_tool_manager_data(include_versions=False)

    assert data["summary"]["total"] == 7
    assert len(data["tools"]) == 7
    assert {item["tool_id"] for item in data["tools"]} == {
        "yt-dlp",
        "ffmpeg",
        "ffprobe",
        "deno",
        "mediainfo",
        "tesseract",
        "mkvtoolnix",
    }


def test_plugin_usage_is_available_for_tool_manager(tmp_path: Path):
    service = ToolService(tmp_path)
    service.register_plugin_tools(
        "mediahub.metadata_editor",
        required_tools=["mediainfo"],
        optional_tools=["tesseract"],
    )

    required = service.find_tool_status("mediainfo", include_version=False)
    optional = service.find_tool_status("tesseract", include_version=False)

    assert required is not None
    assert required["required_by"] == ["mediahub.metadata_editor"]
    assert required["is_required"] is True
    assert optional is not None
    assert optional["optional_by"] == ["mediahub.metadata_editor"]
    assert optional["is_optional"] is True


def test_tool_manager_filters_are_consistent(tmp_path: Path):
    service = ToolService(tmp_path)
    service.register_plugin_tools("plugin.example", required_tools=["mediainfo"])

    plugin_data = service.get_tool_manager_data(
        include_versions=False,
        category="plugin",
        state="used",
    )

    assert [item["tool_id"] for item in plugin_data["tools"]] == ["mediainfo"]
    assert plugin_data["filtered_summary"]["total"] == 1
    assert plugin_data["filtered_summary"]["used"] == 1


def test_get_tools_used_by_supports_mediahub_and_plugins(tmp_path: Path):
    service = ToolService(tmp_path)
    service.register_plugin_tools("plugin.example", required_tools=["mediainfo"])

    mediahub_tools = service.get_tools_used_by("MediaHub")
    plugin_tools = service.get_tools_used_by("plugin.example")

    assert {item["tool_id"] for item in mediahub_tools} == {
        "yt-dlp",
        "ffmpeg",
        "ffprobe",
        "deno",
    }
    assert [item["tool_id"] for item in plugin_tools] == ["mediainfo"]


def test_unknown_filters_raise_clear_error(tmp_path: Path):
    service = ToolService(tmp_path)

    with pytest.raises(ValueError):
        service.get_tool_manager_data(category="other")

    with pytest.raises(ValueError):
        service.get_tool_manager_data(state="broken")


class DummyPlugin:
    def __init__(self, plugin_id, enabled=True, required_tools=None, optional_tools=None):
        self.plugin_id = plugin_id
        self.enabled = enabled
        self.required_tools = required_tools or []
        self.optional_tools = optional_tools or []


def test_synchronize_plugin_tools_ignores_disabled_plugins(tmp_path: Path):
    service = ToolService(tmp_path)
    plugins = [
        DummyPlugin("plugin.active", True, ["mediainfo"], ["tesseract"]),
        DummyPlugin("plugin.disabled", False, ["mkvtoolnix"]),
    ]

    changed = service.synchronize_plugin_tools(plugins)

    assert changed is True
    assert service.get_tools_used_by("plugin.active")
    assert service.get_tools_used_by("plugin.disabled") == []
    assert service.find_tool_status("mkvtoolnix", include_version=False)["is_unused"] is True


def test_synchronize_plugin_tools_notifies_only_on_real_change(tmp_path: Path):
    service = ToolService(tmp_path)
    calls = []
    service.add_change_listener(lambda: calls.append("changed"))
    plugins = [DummyPlugin("plugin.example", True, ["mediainfo"])]

    assert service.synchronize_plugin_tools(plugins) is True
    assert service.synchronize_plugin_tools(plugins) is False
    assert calls == ["changed"]

    plugins[0].enabled = False
    assert service.synchronize_plugin_tools(plugins) is True
    assert calls == ["changed", "changed"]


def test_tool_status_contains_lifecycle_fields(tmp_path: Path):
    service = ToolService(tmp_path)
    status = service.find_tool_status("mediainfo", include_version=False)

    assert status is not None
    assert status["installation_source"] == "Nicht installiert"
    assert status["latest_version"] == "noch nicht geprüft"
    assert status["update_available"] is None
    assert status["can_install"] is True


def test_local_core_tool_reports_mediahub_source(tmp_path: Path):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.yt_dlp.write_bytes(b"test")

    status = service.find_tool_status("yt-dlp", include_version=False)

    assert status is not None
    assert status["installed"] is True
    assert status["installation_source"] == "MediaHub-Toolordner (portabel)"


def test_update_check_uses_cached_result(tmp_path: Path, monkeypatch):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.yt_dlp.write_bytes(b"test")
    monkeypatch.setattr(service, "_get_version", lambda *args, **kwargs: "2026.07.01")
    monkeypatch.setattr(service, "_github_latest_version", lambda url: "2026.07.15")

    result = service.check_tool_update("yt-dlp")
    status = service.find_tool_status("yt-dlp", include_version=False)

    assert result["update_available"] is True
    assert status["latest_version"] == "2026.07.15"
    assert status["update_status"] == "Update verfügbar"


def test_tool_without_online_source_requires_manual_check(tmp_path: Path, monkeypatch):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.ffmpeg.write_bytes(b"test")
    monkeypatch.setattr(service, "_get_version", lambda *args, **kwargs: "ffmpeg version 8.0")

    result = service.check_tool_update("ffmpeg")

    assert result["update_available"] is None
    assert result["update_status"] == "Manuelle Prüfung erforderlich"


def test_safe_replace_rolls_back_on_validation_error(tmp_path: Path):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    target = service.yt_dlp
    staged = tmp_path / "new.exe"
    target.write_bytes(b"old")
    staged.write_bytes(b"new")

    with pytest.raises(RuntimeError):
        service._safe_replace_tool_files(
            {target: staged},
            validator=lambda: (_ for _ in ()).throw(RuntimeError("kaputt")),
        )

    assert target.read_bytes() == b"old"


def test_safe_replace_keeps_new_file_after_success(tmp_path: Path):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    target = service.yt_dlp
    staged = tmp_path / "new.exe"
    target.write_bytes(b"old")
    staged.write_bytes(b"new")

    service._safe_replace_tool_files({target: staged}, validator=lambda: None)

    assert target.read_bytes() == b"new"


def test_safe_update_flags_for_mediahub_tools(tmp_path: Path):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.yt_dlp.write_bytes(b"test")
    service.deno.write_bytes(b"test")

    yt_status = service.find_tool_status("yt-dlp", include_version=False)
    deno_status = service.find_tool_status("deno", include_version=False)
    ffmpeg_status = service.find_tool_status("ffmpeg", include_version=False)

    assert yt_status["safe_update_supported"] is True
    assert yt_status["can_update"] is True
    assert yt_status["can_reinstall"] is True
    assert yt_status["update_method"] == "mediahub_safe"
    assert deno_status["safe_update_supported"] is True
    assert ffmpeg_status["safe_update_supported"] is False


def test_update_mediahub_tool_replaces_ytdlp(tmp_path: Path, monkeypatch):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.yt_dlp.write_bytes(b"old")

    def fake_download(url, target, log_callback=None, timeout=300):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"new")

    monkeypatch.setattr(service, "download_file", fake_download)
    monkeypatch.setattr(service, "_validate_tool_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "get_tool_status", lambda tool_id, include_version=True: {"tool_id": tool_id, "version": "new"})

    result = service.update_mediahub_tool("yt-dlp")

    assert service.yt_dlp.read_bytes() == b"new"
    assert result["tool_id"] == "yt-dlp"


def test_tool_assistant_status_counts_cached_updates(tmp_path: Path, monkeypatch):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.yt_dlp.write_bytes(b"test")
    monkeypatch.setattr(service, "_get_version", lambda *args, **kwargs: "2026.07.01")
    monkeypatch.setattr(service, "_github_latest_version", lambda url: "2026.07.15")

    service.check_tool_update("yt-dlp")
    data = service.get_tool_assistant_status(include_versions=False)

    assert data["updates_available"] == 1
    assert data["safe_updates_available"] == 1
    assert [item["tool_id"] for item in data["safe_update_tools"]] == ["yt-dlp"]


def test_update_all_available_safe_tools_only_runs_marked_updates(tmp_path: Path, monkeypatch):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.yt_dlp.write_bytes(b"test")
    service.deno.write_bytes(b"test")
    service._update_cache["yt-dlp"] = {
        "latest_version": "2026.07.15",
        "update_available": True,
        "update_status": "Update verfügbar",
    }
    service._update_cache["deno"] = {
        "latest_version": "2.5.1",
        "update_available": False,
        "update_status": "Aktuell",
    }
    called = []
    monkeypatch.setattr(
        service,
        "update_mediahub_tool",
        lambda tool_id: called.append(tool_id) or {"version": "neu"},
    )

    results = service.update_all_available_safe_tools()

    assert called == ["yt-dlp"]
    assert results[0]["success"] is True


def test_install_missing_required_tools_combines_core_and_plugin_tools(tmp_path: Path, monkeypatch):
    service = ToolService(tmp_path)
    service.register_plugin_tools("plugin.example", required_tools=["mediainfo"])

    state = {
        "core_missing": ["yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe", "deno.exe"],
        "plugin_missing": ["mediainfo"],
    }

    monkeypatch.setattr(service, "missing_tools", lambda: list(state["core_missing"]))

    def fake_download_missing_tools(log_callback=None):
        state["core_missing"] = []

    monkeypatch.setattr(service, "download_missing_tools", fake_download_missing_tools)
    monkeypatch.setattr(
        service,
        "get_tool_status",
        lambda tool_id, include_version=True: {
            "tool_id": tool_id,
            "display_name": tool_id,
            "installed": True,
        },
    )

    def fake_install_plugin_tools(log_callback=None):
        state["plugin_missing"] = []
        return [{"tool_id": "mediainfo", "display_name": "MediaInfo CLI", "installed": True}]

    monkeypatch.setattr(service, "install_missing_required_plugin_tools", fake_install_plugin_tools)

    result = service.install_missing_required_tools()

    assert {item["tool_id"] for item in result} == {
        "yt-dlp",
        "ffmpeg",
        "ffprobe",
        "deno",
        "mediainfo",
    }


def test_new_folder_layout_is_preferred(tmp_path: Path):
    service = ToolService(tmp_path)
    service.ensure_tools_dir()
    service.yt_dlp.write_bytes(b"new")
    legacy = tmp_path / "tools" / "yt-dlp.exe"
    legacy.write_bytes(b"old")

    assert service.tool_path("yt-dlp") == service.yt_dlp
    assert service.tool_path("yt-dlp").read_bytes() == b"new"


def test_legacy_tool_is_migrated_to_new_folder(tmp_path: Path):
    legacy = tmp_path / "tools" / "yt-dlp.exe"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy")

    service = ToolService(tmp_path)
    service.ensure_tools_dir()

    assert service.yt_dlp.exists()
    assert service.yt_dlp.read_bytes() == b"legacy"
    assert service.tool_path("yt-dlp") == service.yt_dlp
    assert (service.yt_dlp.parent / "manifest.json").exists()


def test_plugin_tools_never_fall_back_to_program_files(tmp_path: Path, monkeypatch):
    service = ToolService(tmp_path)
    monkeypatch.setattr("shutil.which", lambda name: r"C:\Program Files\MediaInfo\mediainfo.exe")

    path = service.tool_path("mediainfo")

    assert path == tmp_path / "tools" / "mediainfo" / "mediainfo.exe"
    assert not path.exists()
