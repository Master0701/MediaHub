from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass(frozen=True, slots=True)
class CapabilityProviderRecord:
    capability: str
    owner_id: str
    provider: Any


class CapabilityRegistry:
    """Runtime registry shared by all MediaHub plugins.

    Providers are registered by capability id and automatically removed when
    their owning plugin stops. The registry never executes providers itself;
    consumers resolve a provider and call the capability-specific contract.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._providers: dict[str, CapabilityProviderRecord] = {}

    @staticmethod
    def _key(capability: str) -> str:
        key = str(capability or "").strip()
        if not key:
            raise ValueError("capability darf nicht leer sein.")
        return key

    def register(self, capability: str, provider: Any, *, owner_id: str) -> None:
        key = self._key(capability)
        owner = str(owner_id or "").strip()
        if not owner:
            raise ValueError("owner_id darf nicht leer sein.")
        if provider is None:
            raise ValueError("provider darf nicht None sein.")
        with self._lock:
            current = self._providers.get(key)
            if current is not None and current.owner_id != owner:
                raise RuntimeError(
                    f"Capability '{key}' ist bereits durch '{current.owner_id}' belegt."
                )
            self._providers[key] = CapabilityProviderRecord(key, owner, provider)

    def unregister_owner(self, owner_id: str) -> int:
        owner = str(owner_id or "").strip()
        with self._lock:
            keys = [key for key, item in self._providers.items() if item.owner_id == owner]
            for key in keys:
                self._providers.pop(key, None)
            return len(keys)

    def resolve(self, capability: str) -> Any | None:
        key = str(capability or "").strip()
        if not key:
            return None
        with self._lock:
            item = self._providers.get(key)
            return item.provider if item is not None else None

    def status(self) -> dict[str, dict[str, str]]:
        with self._lock:
            return {
                key: {
                    "capability": item.capability,
                    "owner_id": item.owner_id,
                    "provider": item.provider.__class__.__name__,
                }
                for key, item in sorted(self._providers.items())
            }
