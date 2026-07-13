from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class WebRuntimeSettings:
    network_mode: str = "computer_only"
    port: int = 8765
    device_name: str = "MediaHub-PC"
    pairing_required: bool = True

    @property
    def host(self) -> str:
        return "0.0.0.0" if self.network_mode == "home_network" else "127.0.0.1"


class WebRuntimeSettingsStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / "config" / "plugins" / "mediahub_web_runtime.json"

    def load(self) -> WebRuntimeSettings:
        if not self.path.exists():
            value = WebRuntimeSettings(device_name=_default_device_name())
            self.save(value)
            return value
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        return self.validate(data)

    def validate(self, data: dict[str, Any] | None) -> WebRuntimeSettings:
        data = dict(data or {})
        mode = str(data.get("network_mode") or "computer_only").strip()
        if mode not in {"computer_only", "home_network"}:
            mode = "computer_only"
        try:
            port = int(data.get("port", 8765))
        except (TypeError, ValueError):
            port = 8765
        if not 1024 <= port <= 65535:
            raise ValueError("Der Port muss zwischen 1024 und 65535 liegen.")
        device_name = str(data.get("device_name") or _default_device_name()).strip()[:80]
        if not device_name:
            device_name = _default_device_name()
        pairing_required = bool(data.get("pairing_required", True))
        return WebRuntimeSettings(network_mode=mode, port=port, device_name=device_name, pairing_required=pairing_required)

    def save(self, settings: WebRuntimeSettings | dict[str, Any]) -> WebRuntimeSettings:
        value = settings if isinstance(settings, WebRuntimeSettings) else self.validate(settings)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(self.path)
        return value


def _default_device_name() -> str:
    return socket.gethostname() or "MediaHub-PC"


def find_private_ipv4() -> str:
    candidates: list[str] = []
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if address not in candidates:
                candidates.append(address)
    except OSError:
        pass
    for address in candidates:
        if address.startswith("10.") or address.startswith("192.168."):
            return address
        if address.startswith("172."):
            try:
                second = int(address.split(".", 2)[1])
                if 16 <= second <= 31:
                    return address
            except (ValueError, IndexError):
                pass
    return ""


def connection_info(settings: WebRuntimeSettings) -> dict[str, Any]:
    lan_ip = find_private_ipv4()
    local_url = f"http://127.0.0.1:{settings.port}/"
    network_url = f"http://{lan_ip}:{settings.port}/" if lan_ip else ""
    active_url = network_url if settings.network_mode == "home_network" and network_url else local_url
    return {
        "network_mode": settings.network_mode,
        "host": settings.host,
        "port": settings.port,
        "device_name": settings.device_name,
        "pairing_required": settings.pairing_required,
        "local_url": local_url,
        "network_url": network_url,
        "active_url": active_url,
        "lan_ip": lan_ip,
    }
