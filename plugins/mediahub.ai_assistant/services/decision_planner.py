from __future__ import annotations
from pathlib import Path
from typing import Any

class DecisionPlanner:
    """Erzeugt einen gemeinsamen, noch nicht ausführenden Änderungsplan."""
    SUPPORTED_MEDIA_TYPES = ("movie", "series", "episode", "special", "video", "audiobook", "other")

    def build(self, analysis: dict[str, Any]) -> dict[str, Any]:
        ident=analysis.get("identification") or {}
        path=Path((analysis.get("file") or {}).get("path") or "")
        media_type=ident.get("media_type") or "other"
        return {
            "schema_version": 1,
            "status": "proposal",
            "media_type": media_type,
            "source_path": str(path) if path else None,
            "rename": {"enabled": False, "proposed_name": None, "proposed_folder": None},
            "metadata": {"enabled": False, "title": ident.get("title_candidate"), "year": ident.get("year"), "season": ident.get("season"), "episodes": ident.get("episodes") or []},
            "local_assets": {"nfo_required": None, "poster_required": None, "fanart_required": None},
            "review": {"required": True, "reason": "Vorschau und Bestätigung sind vor jeder Änderung erforderlich."},
            "execution": {"performed": False, "handlers": {"renamer": "mediahub.universal_renamer", "metadata_editor": "mediahub.metadata_editor"}},
        }
