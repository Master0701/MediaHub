from __future__ import annotations

from typing import Any

from services.online_result_ranker import OnlineResultRanker


class OnlineAgent:
    """Führt geeignete Quellen aus und vereinheitlicht deren Ergebnisse."""

    def __init__(self, source_manager):
        self.source_manager = source_manager
        self.ranker = OnlineResultRanker()

    def run(self, analysis: dict[str, Any]) -> dict[str, Any]:
        query = self.source_manager.build_query(analysis)
        provider_results = self.source_manager.execute(query)
        ranking = self.ranker.rank(query, provider_results)
        return {
            "schema_version": 2,
            "executed": True,
            "query": query,
            "provider_results": provider_results,
            "ranking": ranking,
            "successful_sources": sum(1 for item in provider_results if item.get("status") in {"ok", "success", "ready"}),
            "failed_sources": sum(1 for item in provider_results if item.get("status") in {"error", "failed"}),
        }
