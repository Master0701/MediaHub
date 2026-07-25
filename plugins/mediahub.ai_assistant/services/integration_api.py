from __future__ import annotations

from copy import deepcopy
from typing import Any


class AssistantIntegrationAPI:
    """Stabile, schreibgeschützte Übergabe an Metadata Editor und Universal Renamer."""

    SCHEMA_VERSION = 1

    @classmethod
    def build(cls, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        decision = analysis.get("decision") or {}
        quality = analysis.get("quality") or {}
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "producer": "mediahub.ai_assistant",
            "producer_version": "1.0.0",
            "source": deepcopy(analysis.get("file") or {}),
            "identity": {
                "media_type": decision.get("media_type") or identification.get("media_type"),
                "title": decision.get("title_candidate") or identification.get("title_candidate"),
                "year": identification.get("year"),
                "season": decision.get("season"),
                "episodes": deepcopy(decision.get("episodes") or []),
                "edition": identification.get("edition_candidate"),
                "confidence": decision.get("confidence"),
                "status": decision.get("status"),
            },
            "explanation": deepcopy(decision.get("explanation") or {}),
            "quality": {
                "overall_score": quality.get("overall_score"),
                "status": quality.get("status"),
                "label": quality.get("label"),
                "recommendation": deepcopy(quality.get("recommendation") or {}),
            },
            "proposed_actions": {
                "metadata_editor": deepcopy((analysis.get("change_plan") or {}).get("metadata") or {}),
                "universal_renamer": deepcopy((analysis.get("change_plan") or {}).get("rename") or {}),
            },
            "safety": {
                "automatic_change_allowed": False,
                "preview_required": True,
                "confirmation_required": True,
            },
        }
