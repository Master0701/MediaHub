from __future__ import annotations

from pathlib import Path
from typing import Any


def resolve_mediahub_base_dir(mediahub_api: Any, plugin_path: Path) -> Path:
    """Ermittelt den MediaHub-Hauptordner ohne feste Windows-Pfade."""
    candidates: list[Path] = []

    for attr in ("base_dir", "root_dir", "app_dir", "application_dir"):
        value = getattr(mediahub_api, attr, None) if mediahub_api is not None else None
        if value:
            candidates.append(Path(value))

    # Installierte Plugins liegen üblicherweise unter <MediaHub>/plugins/<plugin-id>.
    candidates.extend(plugin_path.parents)

    for candidate in candidates:
        candidate = candidate.resolve()
        if (candidate / "config" / "mediahub.sqlite3").exists():
            return candidate
        if (candidate / "config").is_dir() and (candidate / "plugins").is_dir():
            return candidate

    # Sicherer Fallback für Entwicklung/Portable-Betrieb.
    return plugin_path.resolve().parent.parent


def resolve_database_paths(mediahub_api: Any, plugin_path: Path) -> tuple[Path, Path, Path]:
    base_dir = resolve_mediahub_base_dir(mediahub_api, plugin_path)
    config_dir = base_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return base_dir, config_dir / "mediahub.sqlite3", config_dir / "knowledge.sqlite3"
