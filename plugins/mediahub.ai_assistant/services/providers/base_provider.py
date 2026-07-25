from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderResult:
    provider_id: str
    provider_name: str
    status: str
    matches: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "status": self.status,
            "matches": self.matches,
            "message": self.message,
        }


class BaseProvider:
    provider_type = "base"

    def __init__(self, config: dict[str, Any]):
        self.config = dict(config)
        self.id = str(config.get("id") or "unknown")
        self.name = str(config.get("name") or self.id)
        self.enabled = bool(config.get("enabled", False))

    def status(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.provider_type,
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "media_types": list(self.config.get("media_types") or []),
            "priority": int(self.config.get("priority", 50)),
            "trust": float(self.config.get("trust", 0.5)),
        }

    def is_configured(self) -> bool:
        return self.enabled

    def search(self, query: dict[str, Any]) -> ProviderResult:
        return ProviderResult(self.id, self.name, "not_implemented", message="Provider-Grundklasse")
