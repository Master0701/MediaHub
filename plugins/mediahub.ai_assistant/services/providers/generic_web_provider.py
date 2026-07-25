from __future__ import annotations

from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult


class GenericWebProvider(BaseProvider):
    provider_type = "generic_web"

    def is_configured(self) -> bool:
        rules = self.config.get("rules") or {}
        return self.enabled and bool(str(self.config.get("search_url") or "").strip()) and bool(rules)

    def search(self, query: dict[str, Any]) -> ProviderResult:
        status = "ready" if self.is_configured() else "not_configured"
        return ProviderResult(
            self.id,
            self.name,
            status,
            message="Webseiten-Scanner registriert." if status == "ready" else "Suchadresse oder Scan-Regeln fehlen.",
        )
