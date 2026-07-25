from __future__ import annotations

import hashlib
import json
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

GITHUB_REPOSITORY = "Master0701/MediaHub_Plugins"
DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/"
    f"{GITHUB_REPOSITORY}/main/catalog/plugin_catalog.json"
)


@dataclass(frozen=True)
class CatalogPlugin:
    plugin_id: str
    name: str
    version: str
    description: str
    visible: bool
    auto_install: bool
    manual_only: bool
    release_asset: str
    sha256_asset: str
    project_page: str
    manual_install_message: str


class PluginCatalogService:
    def __init__(
        self,
        catalog_url: str = DEFAULT_CATALOG_URL,
    ):
        self.catalog_url = catalog_url

    def fetch_catalog(self) -> list[CatalogPlugin]:
        request = urllib.request.Request(
            self.catalog_url,
            headers={
                "User-Agent": "MediaHub-PluginCenter",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

        result = []

        for item in payload.get("plugins", []):
            if not bool(item.get("visible", True)):
                continue

            result.append(
                CatalogPlugin(
                    plugin_id=str(item.get("id") or ""),
                    name=str(
                        item.get("name")
                        or item.get("id")
                        or ""
                    ),
                    version=str(item.get("version") or ""),
                    description=str(
                        item.get("description") or ""
                    ),
                    visible=True,
                    auto_install=bool(
                        item.get("auto_install", True)
                    ),
                    manual_only=bool(
                        item.get("manual_only", False)
                    ),
                    release_asset=str(
                        item.get("release_asset") or ""
                    ),
                    sha256_asset=str(
                        item.get("sha256_asset") or ""
                    ),
                    project_page=str(
                        item.get("project_page")
                        or (
                            "https://github.com/"
                            f"{GITHUB_REPOSITORY}"
                        )
                    ),
                    manual_install_message=str(
                        item.get(
                            "manual_install_message"
                        )
                        or ""
                    ),
                )
            )

        return result

    def download_plugin(
        self,
        plugin: CatalogPlugin,
        progress: Callable[[int, int], None] | None = None,
    ) -> Path:
        if not plugin.auto_install or plugin.manual_only:
            raise PermissionError(
                plugin.manual_install_message
                or (
                    "Dieses Plugin darf nicht automatisch "
                    "installiert werden."
                )
            )

        if not plugin.release_asset:
            raise ValueError(
                "Für dieses Plugin ist kein Release-Paket hinterlegt."
            )

        base = (
            "https://github.com/"
            f"{GITHUB_REPOSITORY}/releases/download/"
            f"v{plugin.version}"
        )
        package_name = plugin.release_asset.format(
            version=plugin.version
        )
        checksum_name = plugin.sha256_asset.format(
            version=plugin.version
        )

        package_url = f"{base}/{package_name}"
        checksum_url = f"{base}/{checksum_name}"

        target = (
            Path(
                tempfile.mkdtemp(
                    prefix="mediahub_plugin_"
                )
            )
            / package_name
        )

        self._download(
            package_url,
            target,
            progress,
        )

        expected = self._read_checksum(
            checksum_url
        )
        actual = hashlib.sha256(
            target.read_bytes()
        ).hexdigest().lower()

        if expected and actual != expected:
            target.unlink(missing_ok=True)
            raise ValueError(
                "SHA256-Prüfung des Plugin-Pakets "
                "ist fehlgeschlagen."
            )

        return target

    @staticmethod
    def _download(
        url: str,
        target: Path,
        progress=None,
    ) -> None:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MediaHub-PluginCenter"
            },
        )

        with (
            urllib.request.urlopen(
                request,
                timeout=60,
            ) as response,
            target.open("wb") as out,
        ):
            total = int(
                response.headers.get(
                    "Content-Length"
                )
                or 0
            )
            done = 0

            while True:
                chunk = response.read(
                    1024 * 256
                )
                if not chunk:
                    break

                out.write(chunk)
                done += len(chunk)

                if progress:
                    progress(done, total)

    @staticmethod
    def _read_checksum(url: str) -> str:
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "MediaHub-PluginCenter"
                },
            )
            with urllib.request.urlopen(
                request,
                timeout=20,
            ) as response:
                text = response.read().decode(
                    "utf-8",
                    errors="replace",
                ).strip()

            return (
                text.split()[0].lower()
                if text
                else ""
            )
        except Exception:
            return ""
