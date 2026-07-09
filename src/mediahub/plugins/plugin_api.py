from dataclasses import dataclass
from pathlib import Path


@dataclass
class PluginInfo:
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: str
    enabled: bool
    path: Path
    entry: str = ""
    icon: str = ""
    safe_mode: bool = True