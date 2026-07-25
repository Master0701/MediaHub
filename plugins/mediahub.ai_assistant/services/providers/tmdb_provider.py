from __future__ import annotations

import os
from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult
from services.providers.http_client import request_json


class TmdbProvider(BaseProvider):
    provider_type = "tmdb"
    API_BASE = "https://api.themoviedb.org/3"

    def _credential(self) -> tuple[str, str] | None:
        bearer_env = str(self.config.get("bearer_token_env") or "MEDIAHUB_TMDB_BEARER_TOKEN")
        api_key_env = str(self.config.get("api_key_env") or "MEDIAHUB_TMDB_API_KEY")
        if os.environ.get(bearer_env):
            return "bearer", os.environ[bearer_env]
        if os.environ.get(api_key_env):
            return "api_key", os.environ[api_key_env]
        return None

    def is_configured(self) -> bool:
        return self.enabled and self._credential() is not None

    def search(self, query: dict[str, Any]) -> ProviderResult:
        credential = self._credential()
        if not self.enabled:
            return ProviderResult(self.id, self.name, "disabled", message="Quelle ist deaktiviert.")
        if credential is None:
            return ProviderResult(self.id, self.name, "not_configured", message="TMDb-Zugangsdaten fehlen.")

        media_type = str(query.get("media_type") or "").lower()
        endpoint_type = "tv" if media_type == "series" else "movie" if media_type == "movie" else "multi"
        params: dict[str, Any] = {
            "query": query.get("title"),
            "language": self.config.get("language", "de-DE"),
            "include_adult": "false",
            "page": 1,
        }
        if query.get("year"):
            params["first_air_date_year" if endpoint_type == "tv" else "primary_release_year"] = query["year"]

        headers: dict[str, str] = {}
        if credential[0] == "bearer":
            headers["Authorization"] = f"Bearer {credential[1]}"
        else:
            params["api_key"] = credential[1]

        data = request_json(f"{self.API_BASE}/search/{endpoint_type}", params=params, headers=headers)
        matches = []
        for item in (data.get("results") or [])[:10]:
            item_type = item.get("media_type") or ("series" if endpoint_type == "tv" else "movie")
            if item_type == "tv":
                item_type = "series"
            date = item.get("first_air_date") or item.get("release_date") or ""
            matches.append({
                "external_id": str(item.get("id") or ""),
                "title": item.get("name") or item.get("title"),
                "original_title": item.get("original_name") or item.get("original_title"),
                "year": int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None,
                "media_type": item_type,
                "overview": item.get("overview") or "",
                "language": item.get("original_language"),
                "popularity": item.get("popularity"),
                "provider_confidence": min(float(item.get("vote_average") or 0.0) / 10.0, 1.0),
                "raw": {"id": item.get("id"), "poster_path": item.get("poster_path")},
            })
        return ProviderResult(self.id, self.name, "ok", matches, f"{len(matches)} TMDb-Treffer geladen.")
