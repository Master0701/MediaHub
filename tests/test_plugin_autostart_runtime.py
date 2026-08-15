from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_CENTER = ROOT / "src" / "mediahub" / "gui" / "plugin_center.py"


def _source():
    return PLUGIN_CENTER.read_text(encoding="utf-8")


def test_plugin_center_autostarts_after_initial_discovery():
    text = _source()
    assert "self.refresh()\n        self._autostart_enabled_plugins()\n        self.refresh()" in text


def test_autostart_requires_enabled_plugin_and_entry():
    text = _source()
    assert "if not plugin.enabled or not plugin.entry:" in text
    assert "return False" in text


def test_autostart_defaults_true_but_manifest_can_opt_out():
    text = _source()
    assert 'data.get("autostart", True) is not False' in text


def test_autostart_starts_runtime_without_opening_gui():
    text = _source()
    start = text.index("def _autostart_enabled_plugins")
    end = text.index("def _build_ui", start)
    block = text[start:end]
    assert "self.runtime.start(plugin)" in block
    assert "ensure_plugin_gui" not in block
    assert "open_selected_plugin" not in block
    assert "QDesktopServices" not in block


def test_manual_enable_also_attempts_background_autostart():
    text = _source()
    start = text.index("def set_plugin_enabled")
    end = text.index("def remove_plugin", start)
    block = text[start:end]
    assert "self._plugin_autostart_enabled(updated)" in block
    assert "self.runtime.start(updated)" in block


def test_capability_runtime_registration_is_preserved():
    runtime = (
        ROOT / "src" / "mediahub" / "plugins" / "plugin_runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._register_instance_capabilities(plugin, instance)" in runtime
    assert "self.mediahub_api.unregister_plugin_capabilities(plugin.plugin_id)" in runtime
