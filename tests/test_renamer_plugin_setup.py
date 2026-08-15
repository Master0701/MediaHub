from pathlib import Path

from src.mediahub.services.tool_service import ToolService


def test_apply_plugin_tool_defaults(tmp_path: Path):
    defaults = tmp_path / "plugin_defaults"
    (defaults / "Presets").mkdir(parents=True)
    (defaults / "Settings.ini").write_text(
        "[Settings]\nFirstLaunch=0\n",
        encoding="utf-8",
    )
    (defaults / "Presets" / ".gitkeep").write_text("", encoding="utf-8")

    service = ToolService(tmp_path)
    copied = service.apply_plugin_tool_defaults(
        "renamer",
        defaults,
        overwrite=True,
    )

    assert copied == ["Settings.ini"]
    assert (
        tmp_path / "tools" / "renamer" / "Settings.ini"
    ).read_text(encoding="utf-8").startswith("[Settings]")
    assert (tmp_path / "tools" / "renamer" / "Presets").is_dir()
