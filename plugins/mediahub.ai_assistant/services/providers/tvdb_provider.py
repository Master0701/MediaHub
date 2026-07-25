from __future__ import annotations

import os
from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult
from services.providers.http_client import request_json


class TvdbProvider(BaseProvider):
    provider_type = "tvdb"
    API_BASE = "https://api4.thetvdb.com/v4"

    def _api_key(self) -> str:
        return os.environ.get(str(self.config.get("api_key_env") or "MEDIAHUB_TVDB_API_KEY"), "")

    def is_configured(self) -> bool:
        return self.enabled and bool(self._api_key())

    def _token(self) -> str:
        body = {"apikey": self._api_key()}
        pin_env = str(self.config.get("subscriber_pin_env") or "MEDIAHUB_TVDB_SUBSCRIBER_PIN")
        pin = os.environ.get(pin_env)
        if pin:
            body["pin"] = pin
        response = request_json(f"{self.API_BASE}/login", method="POST", body=body)
        token = ((response.get("data") or {}).get("token") or response.get("token") or "")
        if not token:
            raise RuntimeError("TheTVDB lieferte kein Anmeldetoken.")
        return str(token)

    def search(self, query: dict[str, Any]) -> ProviderResult:
        if not self.enabled:
            return ProviderResult(self.id, self.name, "disabled", message="Quelle ist deaktiviert.")
        if not self.is_configured():
            return ProviderResult(self.id, self.name, "not_configured", message="TheTVDB-API-Schlüssel fehlt.")

        media_type = str(query.get("media_type") or "").lower()
        tvdb_type = "series" if media_type == "series" else "movie" if media_type == "movie" else None
        data = request_json(
            f"{self.API_BASE}/search",
            params={"query": query.get("title"), "type": tvdb_type, "limit": 10},
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        matches = []
        for item in (data.get("data") or [])[:10]:
            item_type = str(item.get("type") or tvdb_type or "").lower()
            matches.append({
                "external_id": str(item.get("tvdb_id") or item.get("id") or ""),
                "title": item.get("name") or item.get("seriesName") or item.get("movieName"),
                "original_title": item.get("name_translated") or item.get("name"),
                "year": _year(item.get("year") or item.get("first_air_time")),
                "media_type": "series" if item_type == "series" else "movie" if item_type == "movie" else item_type,
                "overview": item.get("overview") or "",
                "language": item.get("primary_language"),
                "aliases": item.get("aliases") or [],
                "provider_confidence": 0.9 if item.get("name") else 0.7,
                "raw": {"tvdb_id": item.get("tvdb_id"), "slug": item.get("slug")},
            })
        return ProviderResult(self.id, self.name, "ok", matches, f"{len(matches)} TheTVDB-Treffer geladen.")


def _year(value: Any) -> int | None:
    text = str(value or "")
    return int(text[:4]) if len(text) >= 4 and text[:4].isdigit() else None
