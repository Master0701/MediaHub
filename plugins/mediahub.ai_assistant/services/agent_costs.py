from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentCost:
    id: str
    label: str
    cost: int
    category: str
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "cost": self.cost,
            "category": self.category,
            "description": self.description,
        }


class AgentCostModel:
    """Zentrale Aufwandsskala für die stufenweise Medienerkennung."""

    _AGENTS = {
        "filename": AgentCost("filename", "Dateiname", 1, "local", "Schnelle Muster- und Titelerkennung."),
        "folder": AgentCost("folder", "Ordner", 1, "local", "Auswertung der übergeordneten Ordnerstruktur."),
        "mediainfo": AgentCost("mediainfo", "MediaInfo", 1, "local", "Technische Container- und Streamdaten."),
        "ffprobe": AgentCost("ffprobe", "ffprobe", 1, "local", "Technische Stream-, Kapitel- und Laufzeitdaten."),
        "knowledge": AgentCost("knowledge", "Wissensdatenbank", 1, "local", "Lokaler Abgleich mit bekannten Medienbeziehungen."),
        "online": AgentCost("online", "Online-Quellen", 2, "network", "Abgleich mit APIs und konfigurierten Webseiten."),
        "subtitles": AgentCost("subtitles", "Untertitel", 2, "in_video", "Textanalyse vorhandener Untertitelspuren."),
        "ocr": AgentCost("ocr", "OCR", 3, "in_video", "Erkennung von Titelkarten, Logos und eingeblendeten Angaben."),
        "audio": AgentCost("audio", "Audio/Spracherkennung", 4, "in_video", "Analyse markanter Dialoge und Titelhinweise."),
        "in_video": AgentCost("in_video", "Vollständige In-Video-Erkennung", 5, "in_video", "Schlüsselbilder, Szenen, OCR, Audio und Fingerprints."),
    }

    def get(self, agent_id: str) -> AgentCost:
        return self._AGENTS.get(
            agent_id,
            AgentCost(agent_id, agent_id, 5, "unknown", "Unbekannte Agentenstufe."),
        )

    def describe(self) -> list[dict[str, Any]]:
        return [item.as_dict() for item in sorted(self._AGENTS.values(), key=lambda x: (x.cost, x.id))]

    def decorate(self, step: dict[str, Any]) -> dict[str, Any]:
        item = self.get(str(step.get("agent") or "unknown"))
        return {**step, "cost": item.cost, "cost_label": "★" * item.cost, "category": item.category}
