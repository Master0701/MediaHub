from __future__ import annotations

from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult


class GenericApiProvider(BaseProvider):
    provider_type = "generic_api"

    def is_configured(self) -> bool:
        return self.enabled and bool(str(self.config.get("base_url") or "").strip())

    def search(self, query: dict[str, Any]) -> ProviderResult:
        status = "ready" if self.is_configured() else "not_configured"
        return ProviderResult(
            self.id,
            self.name,
            status,
            message="Freie API-Quelle registriert." if status == "ready" else "Base-URL fehlt oder Quelle ist deaktiviert.",
        )
