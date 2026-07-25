from __future__ import annotations

from typing import Any

from services.agent_costs import AgentCostModel


class SupervisorAgent:
    """Plant Agentenstufen und übernimmt den tatsächlichen Abschlusszustand."""

    ONLINE_THRESHOLD = 0.90
    IN_VIDEO_THRESHOLD = 0.72
    FINAL_THRESHOLD = 0.92

    def __init__(self):
        self.costs = AgentCostModel()

    def evaluate(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        local_confidence = float(identification.get("confidence") or 0.0)
        title = str(identification.get("title_candidate") or "").strip()
        external_lookup = bool(identification.get("requires_external_lookup", False))
        online = analysis.get("online") or {}
        ranking = online.get("ranking") or {}
        online_confidence = float(ranking.get("confidence") or 0.0)
        decision = analysis.get("decision") or {}
        decision_confidence = float(decision.get("confidence") or 0.0)
        combined_confidence = max(local_confidence, online_confidence, decision_confidence)
        in_video = analysis.get("in_video") or {}
        in_video_state = str(in_video.get("state") or "")
        in_video_completed = in_video_state == "completed"

        unusable_name = not title or title.lower() in {"video", "movie", "film", "episode", "unknown"}
        steps: list[dict[str, Any]] = []

        if not online.get("executed") and (external_lookup or local_confidence < self.ONLINE_THRESHOLD):
            steps.append(self.costs.decorate({
                "agent": "online", "required": True, "state": "pending",
                "reason": "Lokale Erkennung ist noch nicht eindeutig genug.",
            }))
        elif online.get("executed"):
            steps.append(self.costs.decorate({
                "agent": "online", "required": False, "state": "completed",
                "reason": f"Online-Abgleich ausgeführt; Sicherheit {round(online_confidence * 100)} %.",
            }))

        required_by_score = unusable_name or max(local_confidence, online_confidence) < self.IN_VIDEO_THRESHOLD
        if online.get("executed") and ranking.get("decision") in {"no_match", "ambiguous"}:
            required_by_score = True

        if in_video_completed:
            steps.append(self.costs.decorate({
                "agent": "in_video", "required": False, "state": "completed",
                "reason": f"In-Video-Analyse mit {in_video.get('completed_agents', 0)} Agenten abgeschlossen.",
            }))
        else:
            steps.append(self.costs.decorate({
                "agent": "in_video", "required": required_by_score,
                "state": "pending" if required_by_score else "deferred",
                "reason": (
                    "Datei-, Ordner- und Online-Hinweise reichen nicht aus; Bild, OCR, Untertitel und Audio sollen zusätzliche Beweise liefern."
                    if required_by_score else
                    "Aufwendige Videoanalyse bleibt zurückgestellt und wird erst bei Widersprüchen oder Editionsprüfung aktiviert."
                ),
            }))

        required = [step for step in steps if step["required"] and step["state"] != "completed"]
        if decision:
            decision_status = str(decision.get("status") or "review_recommended")
        elif combined_confidence >= self.FINAL_THRESHOLD and not required:
            decision_status = "sufficient"
        elif required:
            decision_status = "needs_more_evidence"
        else:
            decision_status = "review_recommended"

        return {
            "schema_version": 3,
            "local_confidence": local_confidence,
            "online_confidence": online_confidence,
            "decision_confidence": decision_confidence,
            "combined_confidence": combined_confidence,
            "decision_status": decision_status,
            "next_steps": steps,
            "estimated_remaining_cost": sum(step["cost"] for step in required),
            "automatic_execution": True,
            "cost_scale": self.costs.describe(),
        }
