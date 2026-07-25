from __future__ import annotations

from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult


class BuiltinOnlineProvider(BaseProvider):
    provider_type = "builtin_api"

    def is_configured(self) -> bool:
        if not self.enabled:
            return False
        key_env = str(self.config.get("api_key_env") or "").strip()
        if not key_env:
            return True
        import os
        return bool(os.environ.get(key_env))

    def search(self, query: dict[str, Any]) -> ProviderResult:
        if not self.enabled:
            return ProviderResult(self.id, self.name, "disabled", message="Quelle ist deaktiviert.")
        if not self.is_configured():
            return ProviderResult(self.id, self.name, "not_configured", message="API-Schlüssel fehlt.")
        return ProviderResult(
            self.id,
            self.name,
            "ready",
            message="Provider-Schnittstelle vorbereitet; konkrete API-Abfrage folgt in einer eigenen Ausbaustufe.",
        )
