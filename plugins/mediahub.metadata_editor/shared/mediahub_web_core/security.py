from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class PairingResult:
    token: str
    device_id: str
    device_name: str


class PairingStore:
    """Threadsichere lokale Geräte-Kopplung für die gemeinsame Web-Runtime."""

    _LAST_SEEN_WRITE_INTERVAL = 30.0

    def __init__(self, base_dir: Path):
        self.path = Path(base_dir) / "config" / "plugins" / "mediahub_web_pairing.json"
        self._lock = threading.RLock()
        self._last_seen_write: dict[str, float] = {}
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        with self._lock:
            if self.path.exists():
                try:
                    data = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        data.setdefault("pairing_code", self._new_code())
                        data.setdefault("devices", [])
                        return data
                except Exception:
                    pass
            data = {"pairing_code": self._new_code(), "devices": []}
            self._save_locked(data)
            return data

    def _save_locked(self, data: dict[str, Any] | None = None) -> None:
        if data is not None:
            self._data = data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Eindeutige Temp-Datei verhindert Konflikte auch bei unerwarteten Parallelzugriffen.
        temp = self.path.with_name(f"{self.path.name}.{threading.get_ident()}.{secrets.token_hex(4)}.tmp")
        try:
            temp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(self.path)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except Exception:
                pass

    def _save(self, data: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._save_locked(data)

    @staticmethod
    def _new_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @property
    def pairing_code(self) -> str:
        with self._lock:
            return str(self._data.get("pairing_code") or "")

    def rotate_code(self) -> str:
        with self._lock:
            self._data["pairing_code"] = self._new_code()
            self._save_locked()
            return str(self._data["pairing_code"])

    def devices(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": str(item.get("id") or ""),
                    "name": str(item.get("name") or "Unbekanntes Gerät"),
                    "created_at": str(item.get("created_at") or ""),
                    "last_seen": str(item.get("last_seen") or ""),
                }
                for item in list(self._data.get("devices") or [])
            ]

    def claim(self, code: str, device_name: str) -> PairingResult:
        with self._lock:
            if not secrets.compare_digest(str(code or "").strip(), str(self._data.get("pairing_code") or "")):
                raise ValueError("Der Einmalcode ist ungültig.")
            token = secrets.token_urlsafe(32)
            device_id = secrets.token_hex(8)
            name = str(device_name or "Neues Gerät").strip()[:100] or "Neues Gerät"
            now = _now()
            devices = list(self._data.get("devices") or [])
            devices.append({
                "id": device_id,
                "name": name,
                "token_hash": _hash_token(token),
                "created_at": now,
                "last_seen": now,
            })
            self._data["devices"] = devices[-50:]
            self._data["pairing_code"] = self._new_code()
            self._last_seen_write[device_id] = time.monotonic()
            self._save_locked()
            return PairingResult(token=token, device_id=device_id, device_name=name)

    def authorize(self, token: str) -> bool:
        token = str(token or "").strip()
        if not token:
            return False
        digest = _hash_token(token)
        with self._lock:
            for item in list(self._data.get("devices") or []):
                if secrets.compare_digest(str(item.get("token_hash") or ""), digest):
                    device_id = str(item.get("id") or "")
                    now_mono = time.monotonic()
                    last_write = self._last_seen_write.get(device_id, 0.0)
                    # Nicht bei jeder parallelen API-Abfrage auf die Platte schreiben.
                    if now_mono - last_write >= self._LAST_SEEN_WRITE_INTERVAL:
                        item["last_seen"] = _now()
                        self._last_seen_write[device_id] = now_mono
                        self._save_locked()
                    return True
            return False

    def revoke(self, device_id: str) -> bool:
        with self._lock:
            before = list(self._data.get("devices") or [])
            after = [item for item in before if str(item.get("id") or "") != str(device_id or "")]
            if len(after) == len(before):
                return False
            self._data["devices"] = after
            self._last_seen_write.pop(str(device_id or ""), None)
            self._save_locked()
            return True

    def revoke_all(self) -> int:
        with self._lock:
            count = len(list(self._data.get("devices") or []))
            self._data["devices"] = []
            self._last_seen_write.clear()
            self._save_locked()
            return count
