from pathlib import Path

from src.mediahub.plugins.plugin_api import MediaHubPluginAPI


class Provider:
    pass


def api(tmp_path):
    return MediaHubPluginAPI(base_dir=Path(tmp_path), app_version="test")


def test_register_resolve_and_unregister(tmp_path):
    value = api(tmp_path)
    provider = Provider()
    value.register_capability("ai.rename_review", provider, owner_id="mediahub.ai_assistant")
    assert value.resolve_capability("ai.rename_review") is provider
    assert value.get_capability_provider("ai.rename_review") is provider
    assert value.find_capability_provider("ai.rename_review") is provider
    assert value.get_plugin_capability("ai.rename_review") is provider
    assert value.get_runtime_capabilities()["ai.rename_review"]["owner_id"] == "mediahub.ai_assistant"
    assert value.unregister_plugin_capabilities("mediahub.ai_assistant") == 1
    assert value.resolve_capability("ai.rename_review") is None


def test_other_plugin_cannot_silently_replace_capability(tmp_path):
    value = api(tmp_path)
    value.register_capability("ai.rename_review", Provider(), owner_id="one")
    try:
        value.register_capability("ai.rename_review", Provider(), owner_id="two")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Capability collision must be rejected")
