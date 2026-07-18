from __future__ import annotations

import re
from pathlib import Path
from typing import Any


NOISE_TOKENS = {
    "720p", "1080p", "2160p", "4k", "uhd", "hdr", "sdr", "sd", "hd",
    "bluray", "brrip", "webrip", "webdl", "web-dl", "hdtv", "dvdrip",
    "x264", "x265", "h264", "h265", "hevc", "avc", "aac", "ac3", "dts",
    "german", "ger", "deutsch", "english", "eng", "dubbed", "subbed",
    "proper", "repack", "remux"
}

EDITION_PATTERNS = [
    (r"\bextended(?:[\s._-]+edition)?\b", "Extended Edition"),
    (r"\bdirector'?s(?:[\s._-]+cut)?\b", "Director's Cut"),
    (r"\buncut\b", "Uncut"),
    (r"\btheatrical(?:[\s._-]+cut)?\b", "Theatrical Cut"),
    (r"\bremaster(?:ed)?\b", "Remastered"),
    (r"\bultimate(?:[\s._-]+cut|[\s._-]+edition)?\b", "Ultimate Edition"),
]


class FilenameIdentifier:
    SERIES_PATTERNS = (
        re.compile(r"(?i)(?<![A-Z0-9])S(?P<season>\d{1,2})[\s._-]*E(?P<episode>\d{1,3})(?!\d)"),
        re.compile(r"(?i)(?<!\d)(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?!\d)"),
    )

    def identify(self, file_path: str | Path) -> dict[str, Any]:
        name = Path(file_path).stem
        normalized = re.sub(r"[._]+", " ", name)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        media_type = "unknown"
        season = episode = None
        match_span = None

        for pattern in self.SERIES_PATTERNS:
            match = pattern.search(normalized)
            if match:
                media_type = "series"
                season = int(match.group("season"))
                episode = int(match.group("episode"))
                match_span = match.span()
                break

        edition = None
        for pattern, label in EDITION_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                edition = label
                break

        title_part = normalized
        if match_span:
            title_part = (normalized[:match_span[0]] + " " + normalized[match_span[1]:]).strip()
            title_part = re.sub(r"(?i)^(?:rr|proper|repack|rerip)\b", "", title_part).strip()

        # Release-/Gruppenreste und Qualitätsmarker entfernen.
        tokens = re.split(r"[\s-]+", title_part)
        cleaned: list[str] = []
        for token in tokens:
            lower = token.lower().strip()
            if not lower or lower in NOISE_TOKENS:
                continue
            if re.fullmatch(r"\d{3,4}p", lower):
                continue
            if re.fullmatch(r"(?:x|h)\.?26[45]", lower):
                continue
            if lower in {"rr", "r", "dl"}:
                continue
            cleaned.append(token)

        # Häufige kurze Releasegruppen am Anfang vorsichtig entfernen.
        if len(cleaned) > 2 and re.fullmatch(r"[a-zA-Z]{2,4}", cleaned[0]):
            cleaned = cleaned[1:]

        title = " ".join(cleaned).strip(" -_.")
        title = re.sub(r"\s+", " ", title)

        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", normalized)
        year = int(year_match.group(1)) if year_match else None
        if year:
            title = re.sub(rf"\b{year}\b", "", title).strip()

        confidence = 0.25
        reasons: list[str] = []
        if title:
            confidence += 0.25
            reasons.append("bereinigter Dateiname")
        if media_type == "series":
            confidence += 0.35
            reasons.append("Staffel-/Folgenmuster")
        if year:
            confidence += 0.05
            reasons.append("Jahresangabe")
        if edition:
            confidence += 0.05
            reasons.append("Editionshinweis")

        return {
            "media_type": media_type,
            "title_candidate": title or None,
            "season": season,
            "episode": episode,
            "year": year,
            "edition_candidate": edition,
            "confidence": round(min(confidence, 0.95), 2),
            "reasons": reasons,
            "source_name": Path(file_path).name,
        }
