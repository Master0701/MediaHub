from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _number_score(expected: Any, actual: Any) -> float:
    if expected in (None, "", []):
        return 0.5
    if actual in (None, "", []):
        return 0.35
    try:
        expected_values = expected if isinstance(expected, list) else [expected]
        actual_values = actual if isinstance(actual, list) else [actual]
        return 1.0 if {int(v) for v in expected_values} == {int(v) for v in actual_values} else 0.0
    except (TypeError, ValueError):
        return 0.35


class OnlineResultRanker:
    """Vereinheitlicht und bewertet Treffer mehrerer Quellen."""

    WEIGHTS = {
        "title": 0.40,
        "year": 0.15,
        "media_type": 0.20,
        "season_episode": 0.15,
        "runtime": 0.05,
        "provider": 0.05,
    }

    def rank(self, query: dict[str, Any], provider_results: list[dict[str, Any]]) -> dict[str, Any]:
        ranked: list[dict[str, Any]] = []
        query_title = _normalize(query.get("title"))
        query_year = query.get("year")
        query_type = str(query.get("media_type") or "").lower()

        for provider in provider_results:
            trust = min(max(float(provider.get("trust") or 0.5), 0.0), 1.0)
            priority = min(max(int(provider.get("priority") or 50) / 100.0, 0.0), 1.0)
            provider_score = trust * 0.8 + priority * 0.2
            for raw_match in provider.get("matches") or []:
                match = dict(raw_match)
                titles = [match.get("title"), match.get("original_title"), *(match.get("aliases") or [])]
                title_similarity = max(
                    (SequenceMatcher(None, query_title, _normalize(value)).ratio() for value in titles if value),
                    default=0.0,
                )

                year_score = 0.5
                if query_year and match.get("year"):
                    try:
                        difference = abs(int(query_year) - int(match.get("year")))
                        year_score = 1.0 if difference == 0 else 0.65 if difference == 1 else 0.15 if difference <= 3 else 0.0
                    except (TypeError, ValueError):
                        year_score = 0.5

                candidate_type = str(match.get("media_type") or match.get("type") or "").lower()
                type_score = 0.5 if not query_type or not candidate_type else (1.0 if query_type == candidate_type else 0.0)

                season_score = _number_score(query.get("season"), match.get("season"))
                episode_score = _number_score(query.get("episodes"), match.get("episodes") or match.get("episode"))
                season_episode_score = season_score * 0.45 + episode_score * 0.55

                runtime_score = 0.5
                if query.get("duration_seconds") and match.get("duration_seconds"):
                    try:
                        difference = abs(float(query["duration_seconds"]) - float(match["duration_seconds"]))
                        runtime_score = 1.0 if difference <= 120 else 0.75 if difference <= 300 else 0.25 if difference <= 900 else 0.0
                    except (TypeError, ValueError):
                        runtime_score = 0.5

                score = (
                    title_similarity * self.WEIGHTS["title"]
                    + year_score * self.WEIGHTS["year"]
                    + type_score * self.WEIGHTS["media_type"]
                    + season_episode_score * self.WEIGHTS["season_episode"]
                    + runtime_score * self.WEIGHTS["runtime"]
                    + provider_score * self.WEIGHTS["provider"]
                )
                ranked.append({
                    **match,
                    "provider_id": provider.get("provider_id"),
                    "provider_name": provider.get("provider_name"),
                    "score": round(score, 4),
                    "score_percent": round(score * 100, 1),
                    "score_details": {
                        "title": round(title_similarity, 4),
                        "year": round(year_score, 4),
                        "media_type": round(type_score, 4),
                        "season_episode": round(season_episode_score, 4),
                        "runtime": round(runtime_score, 4),
                        "provider": round(provider_score, 4),
                        "weights": dict(self.WEIGHTS),
                    },
                })

        ranked.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        best = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        gap = round(float(best["score"]) - float(second["score"]), 4) if best and second else None
        return {
            "schema_version": 2,
            "matches": ranked,
            "best_match": best,
            "match_count": len(ranked),
            "confidence": float(best.get("score") or 0.0) if best else 0.0,
            "confidence_gap": gap,
            "decision": self._decision(best, gap),
            "weights": dict(self.WEIGHTS),
        }

    @staticmethod
    def _decision(best: dict[str, Any] | None, gap: float | None) -> str:
        if not best:
            return "no_match"
        score = float(best.get("score") or 0.0)
        if score >= 0.90 and (gap is None or gap >= 0.08):
            return "strong_match"
        if score >= 0.78 and (gap is None or gap >= 0.03):
            return "probable_match"
        return "ambiguous"
