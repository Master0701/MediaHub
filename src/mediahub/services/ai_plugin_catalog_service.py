"""Katalogdienst für Raspberry-Pi-AI-Node-Plugins."""
from __future__ import annotations
import json
import urllib.request
from dataclasses import dataclass
DEFAULT_AI_CATALOG_URL = ("https://raw.githubusercontent.com/" "Master0701/MediaHub_Plugins/main/catalog/ai_plugin_catalog.json")
@dataclass(frozen=True, slots=True)
class AIPluginCatalogEntry:
    plugin_id: str
    name: str
    version: str
    description: str
    package_asset: str
    sha256_asset: str
    project_page: str
class AIPluginCatalogService:
    def __init__(self, catalog_url: str = DEFAULT_AI_CATALOG_URL) -> None:
        self.catalog_url = catalog_url
    def fetch_catalog(self) -> list[AIPluginCatalogEntry]:
        request = urllib.request.Request(self.catalog_url, headers={"User-Agent":"MediaHub-AI-Plugin-Store","Accept":"application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        plugins = payload.get("plugins", [])
        if not isinstance(plugins, list):
            return []
        result = []
        for item in plugins:
            if not isinstance(item, dict) or not bool(item.get("visible", True)):
                continue
            result.append(AIPluginCatalogEntry(str(item.get("id") or item.get("plugin_id") or ""), str(item.get("name") or item.get("id") or ""), str(item.get("version") or ""), str(item.get("description") or ""), str(item.get("package_asset") or item.get("release_asset") or ""), str(item.get("sha256_asset") or ""), str(item.get("project_page") or "")))
        return result
