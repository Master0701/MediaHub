"""Verbindungsschicht zwischen MediaHub und dem MediaHub-AI-Node."""

from __future__ import annotations

from pathlib import Path

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AINodeConnectionConfig:
    """Gespeicherte Verbindungsdaten für den Raspberry-Pi-AI-Node."""

    enabled: bool = False
    host: str = ""
    api_port: int = 8765
    api_token: str = ""
    ssh_port: int = 22
    ssh_username: str = "mediahub"
    install_path: str = "/opt/mediahub/ai-node"

    @property
    def base_url(self) -> str:
        host = self.host.strip().rstrip("/")
        if host.startswith(("http://", "https://")):
            return f"{host}:{self.api_port}"
        return f"http://{host}:{self.api_port}"


@dataclass(frozen=True, slots=True)
class AINodeHealth:
    """Ausgewertete Antwort des AI-Node-Health-Endpunkts."""

    online: bool
    status: str
    version: str
    detected_plugins: int | None = None
    loaded_plugins: int | None = None
    message: str = ""
    raw: dict[str, Any] | None = None


class AINodeConnectionError(RuntimeError):
    """Der MediaHub-AI-Node konnte nicht erreicht oder gelesen werden."""


class AINodeService:
    """Kapselt alle HTTP-Zugriffe auf den MediaHub-AI-Node."""

    def __init__(
        self,
        config: AINodeConnectionConfig,
        *,
        timeout: float = 5.0,
    ) -> None:
        self.config = config
        self.timeout = timeout

    @classmethod
    def from_settings(
        cls,
        settings: dict[str, Any],
        *,
        timeout: float = 5.0,
    ) -> "AINodeService":
        ai = settings.get("ai", {})
        if not isinstance(ai, dict):
            ai = {}

        config = AINodeConnectionConfig(
            enabled=bool(ai.get("node_enabled", False)),
            host=str(ai.get("node_host", "")).strip(),
            api_port=int(ai.get("api_port", 8765)),
            api_token=str(ai.get("api_token", "")).strip(),
            ssh_port=int(ai.get("ssh_port", 22)),
            ssh_username=str(ai.get("ssh_username", "mediahub")).strip(),
            install_path=str(
                ai.get("install_path", "/opt/mediahub/ai-node")
            ).strip(),
        )
        return cls(config, timeout=timeout)

    def health(self) -> AINodeHealth:
        if not self.config.enabled:
            return AINodeHealth(
                online=False,
                status="disabled",
                version="unbekannt",
                message="Raspberry-Pi-AI-Node ist in MediaHub deaktiviert.",
            )

        if not self.config.host:
            return AINodeHealth(
                online=False,
                status="not_configured",
                version="unbekannt",
                message="Keine AI-Node-Adresse konfiguriert.",
            )

        try:
            data = self._request_json("GET", "/health")
        except AINodeConnectionError as error:
            return AINodeHealth(
                online=False,
                status="offline",
                version="unbekannt",
                message=str(error),
            )

        plugins = data.get("plugins", {})
        if not isinstance(plugins, dict):
            plugins = {}

        return AINodeHealth(
            online=True,
            status=str(data.get("status", "unbekannt")),
            version=str(
                data.get("version", data.get("app_version", "unbekannt"))
            ),
            detected_plugins=self._optional_int(plugins.get("detected")),
            loaded_plugins=self._optional_int(plugins.get("loaded")),
            message="AI-Node ist erreichbar.",
            raw=data,
        )

    def list_plugins(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", "/plugins")
        plugins = data.get("plugins", [])

        if not isinstance(plugins, list):
            raise AINodeConnectionError(
                "Die AI-Node-Antwort enthält keine gültige Plugin-Liste."
            )

        return [item for item in plugins if isinstance(item, dict)]

    def create_install_plan(
        self,
        package_path: str | Path,
    ) -> dict[str, Any]:
        path = Path(package_path)
        if not path.is_file():
            raise AINodeConnectionError(
                f"AI-Plugin-Paket wurde nicht gefunden: {path}"
            )
        if path.suffix.lower() not in {".zip", ".mhaiplugin"}:
            raise AINodeConnectionError(
                "AI-Plugins müssen als .mhaiplugin- oder ZIP-Paket vorliegen."
            )

        body = path.read_bytes()
        sha256 = hashlib.sha256(body).hexdigest()
        headers = self._headers()
        headers.update(
            {
                "Content-Type": "application/zip",
                "X-Plugin-SHA256": sha256,
                "X-Plugin-Filename": path.name,
            }
        )
        return self._request_json(
            "POST",
            "/plugins/plan",
            body=body,
            headers=headers,
        )

    def execute_install_plan(
        self,
        plan_id: str,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/plugins/plan/{self._plan_id(plan_id)}/execute",
        )

    def confirm_install_plan(
        self,
        plan_id: str,
        sha256: str,
    ) -> dict[str, Any]:
        headers = self._headers()
        headers["X-Plugin-SHA256"] = sha256.strip().lower()
        return self._request_json(
            "POST",
            f"/plugins/plan/{self._plan_id(plan_id)}/confirm",
            headers=headers,
        )

    def cancel_install_plan(
        self,
        plan_id: str,
    ) -> dict[str, Any]:
        return self._request_json(
            "DELETE",
            f"/plugins/plan/{self._plan_id(plan_id)}",
        )

    def enable_plugin(self, plugin_id: str) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/plugins/{self._plugin_id(plugin_id)}/enable",
        )

    def disable_plugin(self, plugin_id: str) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/plugins/{self._plugin_id(plugin_id)}/disable",
        )

    def remove_plugin(
        self,
        plugin_id: str,
        *,
        create_backup: bool = True,
    ) -> dict[str, Any]:
        query = urllib.parse.urlencode(
            {"create_backup": str(bool(create_backup)).lower()}
        )
        return self._request_json(
            "DELETE",
            f"/plugins/{self._plugin_id(plugin_id)}?{query}",
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            self.config.base_url + path,
            data=body,
            headers=headers or self._headers(),
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            detail = self._http_error_detail(error)
            raise AINodeConnectionError(
                f"AI-Node antwortet mit HTTP {error.code}: {detail}"
            ) from error
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", error)
            raise AINodeConnectionError(
                f"AI-Node nicht erreichbar: {reason}"
            ) from error
        except TimeoutError as error:
            raise AINodeConnectionError(
                "Zeitüberschreitung beim AI-Node."
            ) from error
        except OSError as error:
            raise AINodeConnectionError(
                f"Verbindungsfehler zum AI-Node: {error}"
            ) from error

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise AINodeConnectionError(
                "AI-Node hat ungültiges JSON zurückgegeben."
            ) from error

        if not isinstance(data, dict):
            raise AINodeConnectionError(
                "AI-Node-Antwort besitzt ein ungültiges Format."
            )

        return data

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "MediaHub/AI-Node-Client",
        }

        if self.config.api_token:
            headers["Authorization"] = (
                f"Bearer {self.config.api_token}"
            )

        return headers

    @staticmethod
    def _http_error_detail(
        error: urllib.error.HTTPError,
    ) -> str:
        try:
            raw = error.read().decode("utf-8")
            payload = json.loads(raw)
        except Exception:
            return str(error.reason or "Unbekannter Fehler")

        if isinstance(payload, dict):
            return str(payload.get("detail") or payload)

        return str(payload)

    @staticmethod
    def _plan_id(plan_id: str) -> str:
        value = str(plan_id).strip()
        if not value:
            raise AINodeConnectionError(
                "Keine Installationsplan-ID angegeben."
            )
        return urllib.parse.quote(value, safe="._-")

    @staticmethod
    def _plugin_id(plugin_id: str) -> str:
        value = str(plugin_id).strip()
        if not value:
            raise AINodeConnectionError("Keine AI-Plugin-ID angegeben.")
        return urllib.parse.quote(value, safe="._-")

    @staticmethod
    def _optional_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
