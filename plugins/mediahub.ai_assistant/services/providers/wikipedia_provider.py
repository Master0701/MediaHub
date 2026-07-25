from __future__ import annotations

from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult
from services.providers.http_client import request_json


class WikipediaProvider(BaseProvider):
    provider_type = "wikipedia"

    def is_configured(self) -> bool:
        return self.enabled

    def search(self, query: dict[str, Any]) -> ProviderResult:
        if not self.enabled:
            return ProviderResult(self.id, self.name, "disabled", message="Quelle ist deaktiviert.")
        language = str(self.config.get("language") or "de").split("-")[0]
        api_url = f"https://{language}.wikipedia.org/w/api.php"
        title = str(query.get("title") or "").strip()
        media_hint = " Fernsehserie" if query.get("media_type") == "series" else " Film" if query.get("media_type") == "movie" else ""
        data = request_json(api_url, params={
            "action": "opensearch",
            "search": title + media_hint,
            "limit": 8,
            "namespace": 0,
            "format": "json",
            "origin": "*",
        })
        names = data[1] if isinstance(data, list) and len(data) > 1 else []
        descriptions = data[2] if isinstance(data, list) and len(data) > 2 else []
        urls = data[3] if isinstance(data, list) and len(data) > 3 else []
        matches = []
        for index, name in enumerate(names):
            description = descriptions[index] if index < len(descriptions) else ""
            matches.append({
                "external_id": urls[index] if index < len(urls) else str(name),
                "title": name,
                "original_title": None,
                "year": _extract_year(description),
                "media_type": _infer_type(description, query.get("media_type")),
                "overview": description,
                "url": urls[index] if index < len(urls) else None,
                "provider_confidence": 0.72,
            })
        return ProviderResult(self.id, self.name, "ok", matches, f"{len(matches)} Wikipedia-Treffer geladen.")


def _extract_year(text: str) -> int | None:
    import re
    match = re.search(r"\b(19|20)\d{2}\b", text or "")
    return int(match.group(0)) if match else None


def _infer_type(text: str, fallback: Any) -> str | None:
    lowered = (text or "").lower()
    if "fernsehserie" in lowered or "tv-serie" in lowered:
        return "series"
    if "film" in lowered:
        return "movie"
    return str(fallback) if fallback else None
