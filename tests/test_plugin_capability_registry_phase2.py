from pathlib import Path
from src.mediahub.plugins.plugin_api import MediaHubPluginAPI

class Provider: pass

def test_capability_status_and_has_capability(tmp_path: Path):
    api=MediaHubPluginAPI(base_dir=tmp_path,app_version="test")
    assert api.has_capability("metadata.read") is False
    api.register_capability("metadata.read",Provider(),owner_id="metadata")
    assert api.has_capability("metadata.read") is True
    status=api.capability_status("metadata.read")
    assert status["available"] is True
    assert status["owner_id"]=="metadata"
