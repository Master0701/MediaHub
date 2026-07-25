from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.providers import (
    BuiltinOnlineProvider, GenericApiProvider, GenericWebProvider,
    TmdbProvider, TvdbProvider, WikipediaProvider,
)


class SourceManager:
    """Lädt feste und frei definierbare Online-Quellen aus einer JSON-Datei."""

    def __init__(self, plugin_path: Path):
        self.plugin_path = Path(plugin_path)
        self.config_path = self.plugin_path / "config" / "sources.json"
        self._providers = []
        self.reload()

    def reload(self) -> None:
        data = self._read_config()
        self._providers = [self._create_provider(item) for item in (data.get("sources") or [])]

    def _read_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"schema_version": 1, "sources": []}
        with self.config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("sources.json muss ein JSON-Objekt enthalten.")
        return data

    @staticmethod
    def _create_provider(config: dict[str, Any]):
        kind = str(config.get("type") or "builtin_api").lower()
        provider_id = str(config.get("id") or "").lower()
        if provider_id == "tmdb" or kind == "tmdb":
            return TmdbProvider(config)
        if provider_id == "tvdb" or kind == "tvdb":
            return TvdbProvider(config)
        if provider_id == "wikipedia" or kind == "wikipedia":
            return WikipediaProvider(config)
        if kind == "generic_api":
            return GenericApiProvider(config)
        if kind == "generic_web":
            return GenericWebProvider(config)
        return BuiltinOnlineProvider(config)

    def status(self) -> dict[str, Any]:
        providers = [provider.status() for provider in self._providers]
        return {
            "schema_version": 1,
            "config_path": str(self.config_path),
            "total": len(providers),
            "enabled": sum(1 for item in providers if item["enabled"]),
            "configured": sum(1 for item in providers if item["configured"]),
            "providers": providers,
        }

    def build_query(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        summary = analysis.get("summary") or {}
        return {
            "media_type": identification.get("media_type"),
            "title": identification.get("title_candidate"),
            "year": identification.get("year"),
            "season": identification.get("season"),
            "episodes": identification.get("episodes") or [],
            "duration_seconds": summary.get("duration_seconds"),
        }

    def _supports_query(self, provider, query: dict[str, Any]) -> bool:
        media_types = list(provider.config.get("media_types") or [])
        media_type = query.get("media_type")
        return not media_types or not media_type or media_type in media_types

    def eligible_providers(self, query: dict[str, Any]):
        providers = []
        for provider in self._providers:
            status = provider.status()
            if status["enabled"] and status["configured"] and self._supports_query(provider, query):
                providers.append(provider)
        return sorted(
            providers,
            key=lambda item: int(item.config.get("priority", 50)),
            reverse=True,
        )

    def plan(self, analysis: dict[str, Any]) -> dict[str, Any]:
        query = self.build_query(analysis)
        candidates = [provider.status() for provider in self.eligible_providers(query)]
        return {
            "query": query,
            "candidate_sources": [item["id"] for item in candidates],
            "candidate_details": candidates,
            "executed": False,
            "reason": (
                "Geeignete Quellen wurden gefunden und können automatisch ausgeführt werden."
                if candidates
                else "Keine aktivierte und vollständig konfigurierte Quelle passt zu diesem Medientyp."
            ),
        }

    def execute(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for provider in self.eligible_providers(query):
            status = provider.status()
            try:
                result = provider.search(query).as_dict()
            except Exception as exc:
                result = {
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                    "status": "error",
                    "matches": [],
                    "message": str(exc),
                }
            result["priority"] = status["priority"]
            result["trust"] = status["trust"]
            result["provider_type"] = status["type"]
            results.append(result)
        return results
