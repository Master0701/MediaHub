"""Connection and configuration helpers for MediaHub Compute Nodes."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar


class ComputeNodeConnectionError(RuntimeError):
    """A Compute Node could not be reached or returned invalid data."""


@dataclass(frozen=True)
class ComputeNodeConfig:
    """Configuration for one optional Compute Node."""

    node_id: str
    name: str
    node_type: str
    host: str
    api_port: int
    api_token: str
    enabled: bool = True

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ComputeNodeConfig:
        return cls(
            node_id=str(
                data.get("id")
                or ""
            ).strip(),
            name=str(
                data.get("name")
                or ""
            ).strip(),
            node_type=str(
                data.get("type")
                or "windows_compute"
            ).strip(),
            host=str(
                data.get("host")
                or ""
            ).strip(),
            api_port=int(
                data.get("api_port")
                or 8766
            ),
            api_token=str(
                data.get("api_token")
                or ""
            ).strip(),
            enabled=bool(
                data.get("enabled", True)
            ),
        )

    @property
    def base_url(self) -> str:
        host = self.host.strip().rstrip("/")

        if not host:
            return ""

        if not host.startswith(
            ("http://", "https://")
        ):
            host = f"http://{host}"

        parsed = urllib.parse.urlsplit(host)

        if parsed.port is not None:
            return host

        hostname = parsed.hostname or ""

        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"

        netloc = f"{hostname}:{self.api_port}"

        if parsed.username:
            credentials = parsed.username
            if parsed.password:
                credentials += f":{parsed.password}"
            netloc = f"{credentials}@{netloc}"

        return urllib.parse.urlunsplit(
            (
                parsed.scheme,
                netloc,
                parsed.path.rstrip("/"),
                "",
                "",
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.name,
            "type": self.node_type,
            "enabled": self.enabled,
            "host": self.host,
            "api_port": self.api_port,
            "api_token": self.api_token,
        }


@dataclass(frozen=True)
class ComputeNodeHealth:
    """Result of the public Compute-Node health endpoint."""

    online: bool
    status: str
    service: str
    node_id: str
    message: str = ""
    raw: dict[str, Any] | None = None


class ComputeNodeClient:
    """HTTP client for one MediaHub Windows Compute Node."""

    def __init__(
        self,
        config: ComputeNodeConfig,
        *,
        timeout: float = 5.0,
    ) -> None:
        self.config = config
        self.timeout = float(timeout)

    def health(self) -> ComputeNodeHealth:
        if not self.config.enabled:
            return ComputeNodeHealth(
                online=False,
                status="disabled",
                service="",
                node_id=self.config.node_id,
                message="Compute Node ist deaktiviert.",
            )

        if not self.config.base_url:
            return ComputeNodeHealth(
                online=False,
                status="not_configured",
                service="",
                node_id=self.config.node_id,
                message="Keine Compute-Node-Adresse konfiguriert.",
            )

        try:
            data = self._request_json(
                "GET",
                "/health",
                authenticated=False,
            )
        except ComputeNodeConnectionError as error:
            return ComputeNodeHealth(
                online=False,
                status="offline",
                service="",
                node_id=self.config.node_id,
                message=str(error),
            )

        return ComputeNodeHealth(
            online=True,
            status=str(
                data.get("status")
                or "unknown"
            ),
            service=str(
                data.get("service")
                or ""
            ),
            node_id=str(
                data.get("node_id")
                or self.config.node_id
            ),
            message="Compute Node ist erreichbar.",
            raw=data,
        )

    def identity(self) -> dict[str, Any]:
        return self._request_json(
            "GET",
            "/identity",
        )

    def capabilities(self) -> dict[str, Any]:
        return self._request_json(
            "GET",
            "/capabilities",
        )

    def plugins(self) -> list[dict[str, Any]]:
        data = self._request_json(
            "POST",
            "/plugins",
        )

        plugins = data.get("plugins", [])

        if not isinstance(plugins, list):
            raise ComputeNodeConnectionError(
                "Compute Node hat keine gültige "
                "Plugin-Liste geliefert."
            )

        return [
            item
            for item in plugins
            if isinstance(item, dict)
        ]

    def workers(self) -> list[dict[str, Any]]:
        data = self._request_json(
            "POST",
            "/workers",
        )

        workers = data.get("workers", [])

        if not isinstance(workers, list):
            raise ComputeNodeConnectionError(
                "Compute Node hat keine gültige "
                "Worker-Liste geliefert."
            )

        return [
            item
            for item in workers
            if isinstance(item, dict)
        ]

    def pairing_status(
        self,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            "/pair/status",
            authenticated=False,
        )

    def pair(
        self,
        code: str,
    ) -> dict[str, Any]:
        pairing_code = str(code).strip()

        if not pairing_code:
            raise ComputeNodeConnectionError(
                "Kein Pairing-Code angegeben."
            )

        data = self._request_json(
            "POST",
            "/pair",
            payload={
                "code": pairing_code,
            },
            authenticated=False,
        )

        token = str(
            data.get("api_token")
            or ""
        ).strip()

        if not token:
            raise ComputeNodeConnectionError(
                "Pairing war erfolgreich, aber "
                "der Compute Node hat kein "
                "API-Token geliefert."
            )

        return data

    def inspect(
        self,
    ) -> dict[str, Any]:
        health = self.health()

        result: dict[str, Any] = {
            "health": health,
            "identity": None,
            "capabilities": None,
            "plugins": [],
            "workers": [],
        }

        if not health.online:
            return result

        if not self.config.api_token:
            return result

        result["identity"] = self.identity()
        result["capabilities"] = (
            self.capabilities()
        )
        result["plugins"] = self.plugins()
        result["workers"] = self.workers()

        return result

    def install_plugin(
        self,
        package_path: str | Path,
        *,
        sha256: str,
        replace: bool = False,
    ) -> dict:
        """Installiert ein .mhaiplugin-Paket auf dem Compute Node."""

        package = Path(package_path)

        if not package.is_file():
            raise ComputeNodeConnectionError(
                f"Plugin-Paket nicht gefunden: {package}"
            )

        if package.suffix.lower() != ".mhaiplugin":
            raise ComputeNodeConnectionError(
                "Für Windows Compute Nodes sind nur "
                ".mhaiplugin-Pakete zulässig."
            )

        expected_sha256 = str(
            sha256
        ).strip().lower()

        if len(expected_sha256) != 64:
            raise ComputeNodeConnectionError(
                "Ungültige SHA-256-Prüfsumme."
            )

        headers = {
            "Content-Type": (
                "application/octet-stream"
            ),
            "X-Plugin-Filename": package.name,
            "X-Plugin-SHA256": expected_sha256,
            "X-Plugin-Replace": (
                "true"
                if replace
                else "false"
            ),
        }

        if self.config.api_token:
            headers["Authorization"] = (
                "Bearer "
                + self.config.api_token
            )

        request = urllib.request.Request(
            self.config.base_url
            + "/plugins/install",
            data=package.read_bytes(),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=max(
                    self.timeout,
                    60.0,
                ),
            ) as response:
                payload = response.read()

        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(
                    error.read().decode(
                        "utf-8"
                    )
                )
                message = str(
                    detail.get("detail")
                    or detail.get("error")
                    or error
                )
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                AttributeError,
            ):
                message = str(error)

            raise ComputeNodeConnectionError(
                message
            ) from error

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as error:
            raise ComputeNodeConnectionError(
                "Windows Compute Node konnte "
                "das Plugin-Paket nicht empfangen: "
                f"{error}"
            ) from error

        if not payload:
            return {}

        try:
            result = json.loads(
                payload.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ComputeNodeConnectionError(
                "Windows Compute Node hat eine "
                "ungültige Installationsantwort "
                "zurückgegeben."
            ) from error

        if not isinstance(result, dict):
            raise ComputeNodeConnectionError(
                "Ungültige Installationsantwort "
                "des Windows Compute Nodes."
            )

        return result

    def uninstall_plugin(
        self,
        plugin_id: str,
    ) -> dict[str, Any]:
        """Deinstalliert ein Plugin vom Windows Compute Node."""

        plugin_id = str(plugin_id).strip()

        if not plugin_id:
            raise ComputeNodeConnectionError(
                "Plugin-ID fehlt."
            )

        return self._request_json(
            "POST",
            "/plugins/uninstall",
            payload=None,
            extra_headers={
                "X-Plugin-ID": plugin_id,
            },
        )

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        payload: dict[str, Any] | None = None,
        authenticated: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        base_url = self.config.base_url

        if not base_url:
            raise ComputeNodeConnectionError(
                "Keine Compute-Node-Adresse konfiguriert."
            )

        body: bytes | None = None

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "MediaHub/Compute-Node-Client"
            ),
        }

        if payload is not None:
            body = json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8")

            headers["Content-Type"] = (
                "application/json; charset=utf-8"
            )

        if extra_headers:
            headers.update(extra_headers)

        if authenticated:
            token = self.config.api_token.strip()

            if not token:
                raise ComputeNodeConnectionError(
                    "Für diesen Compute-Node-Endpunkt "
                    "wird ein API-Token benötigt."
                )

            headers["Authorization"] = (
                f"Bearer {token}"
            )

        request = urllib.request.Request(
            base_url + endpoint,
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                raw = response.read().decode(
                    "utf-8"
                )
        except urllib.error.HTTPError as error:
            detail = self._http_error_detail(
                error
            )

            raise ComputeNodeConnectionError(
                "Compute Node antwortet mit "
                f"HTTP {error.code}: {detail}"
            ) from error

        except urllib.error.URLError as error:
            reason = getattr(
                error,
                "reason",
                error,
            )

            raise ComputeNodeConnectionError(
                "Compute Node nicht erreichbar: "
                f"{reason}"
            ) from error

        except TimeoutError as error:
            raise ComputeNodeConnectionError(
                "Zeitüberschreitung beim "
                "Compute Node."
            ) from error

        except OSError as error:
            raise ComputeNodeConnectionError(
                "Verbindungsfehler zum "
                f"Compute Node: {error}"
            ) from error

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ComputeNodeConnectionError(
                "Compute Node hat ungültiges "
                "JSON geliefert."
            ) from error

        if not isinstance(data, dict):
            raise ComputeNodeConnectionError(
                "Compute-Node-Antwort besitzt "
                "ein ungültiges Format."
            )

        return data

    @staticmethod
    def _http_error_detail(
        error: urllib.error.HTTPError,
    ) -> str:
        try:
            raw = error.read().decode(
                "utf-8"
            )
            payload = json.loads(raw)
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return str(
                error.reason
                or "Unbekannter Fehler"
            )

        if isinstance(payload, dict):
            return str(
                payload.get("detail")
                or payload.get("error")
                or payload
            )

        return str(payload)


class ComputeNodeService:
    """Read and access optional Compute Nodes from MediaHub settings."""

    SUPPORTED_TYPES: ClassVar[set[str]] = {
        "windows_compute",
    }

    def __init__(
        self,
        settings_service,
    ) -> None:
        self.settings_service = (
            settings_service
        )

    def list_nodes(
        self,
    ) -> list[ComputeNodeConfig]:
        settings = (
            self.settings_service.load()
        )

        if not isinstance(
            settings,
            dict,
        ):
            return []

        ai = settings.get(
            "ai",
            {},
        )

        if not isinstance(ai, dict):
            return []

        raw_nodes = ai.get(
            "compute_nodes",
            [],
        )

        if not isinstance(
            raw_nodes,
            list,
        ):
            return []

        result: list[
            ComputeNodeConfig
        ] = []

        for raw in raw_nodes:
            if not isinstance(
                raw,
                dict,
            ):
                continue

            node = (
                ComputeNodeConfig.from_dict(
                    raw
                )
            )

            if not node.node_id:
                continue

            if (
                node.node_type
                not in self.SUPPORTED_TYPES
            ):
                continue

            result.append(node)

        return result

    def enabled_nodes(
        self,
    ) -> list[ComputeNodeConfig]:
        return [
            node
            for node in self.list_nodes()
            if node.enabled
        ]

    def find_node(
        self,
        node_id: str,
    ) -> ComputeNodeConfig | None:
        wanted = str(
            node_id
        ).strip()

        for node in self.list_nodes():
            if node.node_id == wanted:
                return node

        return None

    def client_for(
        self,
        node: ComputeNodeConfig,
        *,
        timeout: float = 5.0,
    ) -> ComputeNodeClient:
        return ComputeNodeClient(
            node,
            timeout=timeout,
        )

    def client_for_id(
        self,
        node_id: str,
        *,
        timeout: float = 5.0,
    ) -> ComputeNodeClient:
        node = self.find_node(
            node_id
        )

        if node is None:
            raise ComputeNodeConnectionError(
                "Compute Node wurde in "
                "MediaHub nicht gefunden: "
                f"{node_id}"
            )

        return self.client_for(
            node,
            timeout=timeout,
        )
