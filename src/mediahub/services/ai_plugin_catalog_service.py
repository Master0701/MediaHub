"""Gemeinsamer Katalogdienst für MediaHub-AI-/Compute-Node-Plugins."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

AI_PLUGIN_GITHUB_REPOSITORY = (
    "Master0701/MediaHub_Plugins"
)

AI_PLUGIN_RELEASE_BASE_URL = (
    "https://github.com/"
    f"{AI_PLUGIN_GITHUB_REPOSITORY}/"
    "releases/latest/download"
)

DEFAULT_AI_CATALOG_URL = (
    "https://raw.githubusercontent.com/"
    "Master0701/MediaHub_Plugins/main/"
    "catalog/ai_plugin_catalog.json"
)


def _string_tuple(
    value: object,
) -> tuple[str, ...]:
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()

    if not isinstance(value, list):
        return ()

    result: list[str] = []

    for item in value:
        text = str(item or "").strip()

        if (
            text
            and text not in result
        ):
            result.append(text)

    return tuple(result)


@dataclass(
    frozen=True,
    slots=True,
)
class AIPluginCatalogEntry:
    plugin_id: str
    name: str
    version: str
    description: str
    package_asset: str
    sha256_asset: str
    project_page: str
    targets: tuple[str, ...]
    platforms: tuple[str, ...]
    required_capabilities: tuple[str, ...]

    def supports_target(
        self,
        target: str,
    ) -> bool:
        wanted = str(target).strip()

        return (
            wanted in self.targets
        )

    def supports_platform(
        self,
        platform_name: str,
    ) -> bool:
        if not self.platforms:
            return True

        wanted = (
            str(platform_name)
            .strip()
            .lower()
        )

        return any(
            item.lower() == wanted
            for item in self.platforms
        )

    def capabilities_match(
        self,
        available: set[str],
    ) -> bool:
        required = {
            item.lower()
            for item
            in self.required_capabilities
        }

        actual = {
            str(item).lower()
            for item in available
        }

        return required.issubset(
            actual
        )


class AIPluginCatalogService:
    def __init__(
        self,
        catalog_url: str = (
            DEFAULT_AI_CATALOG_URL
        ),
    ) -> None:
        self.catalog_url = catalog_url

    @staticmethod
    def _download_bytes(
        url: str,
    ) -> bytes:
        url = str(url).strip()

        if not url:
            raise RuntimeError(
                "Download-URL fehlt."
            )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "MediaHub-AI-Plugin-Store"
                ),
                "Accept": (
                    "application/octet-stream"
                ),
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:
            return response.read()

    def download_compute_package(
        self,
        plugin: AIPluginCatalogEntry,
        destination: str,
    ) -> tuple[str, str]:
        """Lädt Paket und SHA256 und prüft beides."""

        import hashlib
        from pathlib import Path

        package_asset = str(
            plugin.package_asset
        ).strip()

        sha_asset = str(
            plugin.sha256_asset
        ).strip()

        if not package_asset:
            raise RuntimeError(
                "Für dieses Plugin fehlt das "
                "Paket-Asset."
            )

        if not sha_asset:
            raise RuntimeError(
                "Für dieses Plugin fehlt das "
                "SHA256-Asset."
            )

        package_name = Path(
            package_asset
        ).name

        sha_name = Path(
            sha_asset
        ).name

        if (
            not package_name
            or package_name != package_asset
        ):
            raise RuntimeError(
                "Ungültiger Paket-Assetname."
            )

        if (
            not sha_name
            or sha_name != sha_asset
        ):
            raise RuntimeError(
                "Ungültiger SHA256-Assetname."
            )

        package_url = (
            f"{AI_PLUGIN_RELEASE_BASE_URL}/"
            f"{package_name}"
        )

        sha_url = (
            f"{AI_PLUGIN_RELEASE_BASE_URL}/"
            f"{sha_name}"
        )

        package_data = self._download_bytes(
            package_url
        )

        sha_data = self._download_bytes(
            sha_url
        )

        sha_text = sha_data.decode(
            "utf-8"
        ).strip()

        expected_sha256 = (
            sha_text.split()[0]
            if sha_text
            else ""
        ).lower()

        if len(expected_sha256) != 64:
            raise RuntimeError(
                "Das SHA256-Asset enthält keine "
                "gültige Prüfsumme."
            )

        actual_sha256 = hashlib.sha256(
            package_data
        ).hexdigest()

        if actual_sha256 != expected_sha256:
            raise RuntimeError(
                "SHA-256-Prüfung fehlgeschlagen. "
                "Das Plugin-Paket wird nicht "
                "installiert."
            )

        destination_path = Path(
            destination
        )

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination_path.write_bytes(
            package_data
        )

        return (
            str(destination_path),
            expected_sha256,
        )

    def fetch_catalog(
        self,
    ) -> list[AIPluginCatalogEntry]:
        request = urllib.request.Request(
            self.catalog_url,
            headers={
                "User-Agent": (
                    "MediaHub-AI-Plugin-Store"
                ),
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:
            payload = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        plugins = payload.get(
            "plugins",
            [],
        )

        if not isinstance(
            plugins,
            list,
        ):
            return []

        result: list[
            AIPluginCatalogEntry
        ] = []

        for item in plugins:
            if not isinstance(
                item,
                dict,
            ):
                continue

            if not bool(
                item.get(
                    "visible",
                    True,
                )
            ):
                continue

            targets = _string_tuple(
                item.get("targets")
            )

            # Rückwärtskompatibilität:
            # alte AI-Katalogeinträge waren
            # ausschließlich für den Pi gedacht.
            if not targets:
                targets = (
                    "raspberry_pi",
                )

            result.append(
                AIPluginCatalogEntry(
                    plugin_id=str(
                        item.get("id")
                        or item.get(
                            "plugin_id"
                        )
                        or ""
                    ),
                    name=str(
                        item.get("name")
                        or item.get("id")
                        or ""
                    ),
                    version=str(
                        item.get("version")
                        or ""
                    ),
                    description=str(
                        item.get(
                            "description"
                        )
                        or ""
                    ),
                    package_asset=str(
                        item.get(
                            "package_asset"
                        )
                        or item.get(
                            "release_asset"
                        )
                        or ""
                    ),
                    sha256_asset=str(
                        item.get(
                            "sha256_asset"
                        )
                        or ""
                    ),
                    project_page=str(
                        item.get(
                            "project_page"
                        )
                        or ""
                    ),
                    targets=targets,
                    platforms=_string_tuple(
                        item.get(
                            "platforms"
                        )
                    ),
                    required_capabilities=(
                        _string_tuple(
                            item.get(
                                "required_capabilities"
                            )
                        )
                    ),
                )
            )

        return result
