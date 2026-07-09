from pathlib import Path
import json
import tempfile

from src.mediahub.docs.plugin_help import markdown_to_plain, load_plugin_help


def test_markdown_to_plain_heading():
    text = markdown_to_plain("# Plugin Hilfe\n\n## Abschnitt\n\n- Punkt 1")

    assert "PLUGIN HILFE" in text
    assert "Abschnitt" in text
    assert "- Punkt 1" in text


def test_load_plugin_help_without_plugins_folder():
    with tempfile.TemporaryDirectory() as temp_dir:
        entries = load_plugin_help(Path(temp_dir))

        assert entries == []


def test_load_plugin_help_reads_help_md():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        plugin_dir = base_dir / "plugins" / "test_plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "Test Plugin"}, ensure_ascii=False),
            encoding="utf-8",
        )

        (plugin_dir / "help.md").write_text(
            "# Test Hilfe\n\nDas ist eine Plugin-Hilfe.",
            encoding="utf-8",
        )

        entries = load_plugin_help(base_dir)

        assert len(entries) == 1
        assert entries[0]["title"] == "Test Plugin"
        assert entries[0]["book"] == "plugin"
        assert entries[0]["key"] == "plugin_test_plugin"
        assert "Plugin-Hilfe" in entries[0]["text"]