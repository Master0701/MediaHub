from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VIDEO_NOISE_TOKENS = {
    "480p", "576p", "720p", "1080p", "1080i", "1440p", "2160p", "4320p",
    "2k", "4k", "8k", "uhd", "hdr", "hdr10", "hdr10plus", "dolbyvision", "dv",
    "sdr", "sd", "hd", "fhd", "bluray", "blu-ray", "bdrip", "brrip", "webrip",
    "webdl", "web-dl", "hdtv", "pdtv", "dvdrip", "dvd", "cam", "telesync",
    "remux", "xvid", "divx", "x264", "x265", "h264", "h265", "hevc", "avc",
    "av1", "vp9", "aac", "ac3", "eac3", "ddp", "dts", "dtshd", "truehd",
    "atmos", "flac", "mp3", "german", "ger", "deutsch", "english", "eng",
    "multi", "multilingual", "dubbed", "subbed", "sub", "subs", "proper", "repack",
    "rerip", "internal", "complete", "final", "limited", "readnfo", "nfofix",
    "sample", "fix", "proof", "dirfix", "subfix", "syncfix", "rsg", "rr", "grp",
}

RELEASE_PREFIXES = {"rr", "r", "rsg", "grp", "dl", "ws", "fs", "ld", "md", "ac3d", "dtsd"}

EDITION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bextended(?:[\s._-]+(?:cut|edition|version))?\b", "Extended Edition"),
    (r"\b(?:director'?s|directors)(?:[\s._-]+cut)?\b", "Director's Cut"),
    (r"\buncut\b", "Uncut"),
    (r"\bunrated\b", "Unrated"),
    (r"\btheatrical(?:[\s._-]+(?:cut|version))?\b", "Theatrical Cut"),
    (r"\bremaster(?:ed)?\b", "Remastered"),
    (r"\brestored\b", "Restored"),
    (r"\bultimate(?:[\s._-]+(?:cut|edition))?\b", "Ultimate Edition"),
    (r"\bfinal(?:[\s._-]+cut)?\b", "Final Cut"),
    (r"\bspecial(?:[\s._-]+edition)?\b", "Special Edition"),
    (r"\bcollector'?s(?:[\s._-]+edition)?\b", "Collector's Edition"),
    (r"\banniversary(?:[\s._-]+edition)?\b", "Anniversary Edition"),
    (r"\bimax(?:[\s._-]+(?:edition|version))?\b", "IMAX Edition"),
    (r"\bopen[\s._-]*matte\b", "Open Matte"),
    (r"\broadshow(?:[\s._-]+version)?\b", "Roadshow Version"),
    (r"\bworkprint\b", "Workprint"),
    (r"\bfan[\s._-]*(?:edit|cut)\b", "Fan Edit"),
    (r"\blong(?:[\s._-]+version)?\b", "Langfassung"),
    (r"\bkinofassung\b", "Kinofassung"),
)


@dataclass(frozen=True)
class EpisodeMatch:
    season: int | None
    episodes: tuple[int, ...]
    span: tuple[int, int]
    special: bool = False
    pattern_name: str = ""


class FilenameIdentifier:
    """Deterministische Erstidentifikation aus Datei- und Ordnernamen.

    Diese Klasse trifft bewusst noch keine Online-Entscheidung. Sie erzeugt
    robuste Kandidaten und Belege für spätere TMDB/TVDB/IMDb-Abgleiche.
    """

    SERIES_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "SxxExx",
            re.compile(
                r"(?i)(?<![A-Z0-9])S(?P<season>\d{1,3})[\s._-]*"
                r"E(?P<episode>\d{1,4})(?:[\s._-]*(?:E|-)[\s._-]*(?P<episode2>\d{1,4}))?(?!\d)"
            ),
        ),
        (
            "x-format",
            re.compile(
                r"(?i)(?<!\d)(?P<season>\d{1,3})x(?P<episode>\d{1,4})"
                r"(?:[\s._-]*(?:x|-)[\s._-]*(?P<episode2>\d{1,4}))?(?!\d)"
            ),
        ),
        (
            "deutsch",
            re.compile(
                r"(?i)\b(?:staffel|season)[\s._-]*(?P<season>\d{1,3})[\s._-]*"
                r"(?:folge|episode|ep)[\s._-]*(?P<episode>\d{1,4})(?!\d)"
            ),
        ),
        (
            "episode-only",
            re.compile(r"(?i)\b(?:folge|episode|ep)[\s._-]*(?P<episode>\d{1,4})(?!\d)"),
        ),
    )

    ABSOLUTE_EPISODE_PATTERN = re.compile(
        r"(?i)(?:^|[\s._-])(?:E|EP|Episode)[\s._-]*(?P<episode>\d{1,4})(?!\d)"
    )
    SPECIAL_PATTERN = re.compile(
        r"(?i)(?<![A-Z0-9])(?:S00[\s._-]*E(?P<s00>\d{1,4})|SP(?P<sp>\d{1,4})|SPECIAL[\s._-]*(?P<special>\d{1,4}))(?!\d)"
    )
    YEAR_PATTERN = re.compile(r"(?<!\d)(?P<year>18\d{2}|19\d{2}|20\d{2}|2100)(?!\d)")
    DISC_PATTERN = re.compile(r"(?i)\b(?:cd|disc|disk|dvd|part|teil)[\s._-]*(\d{1,2})\b")

    def identify(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        source_stem = path.stem
        normalized = self._normalize(source_stem)
        parent_candidates = self._parent_candidates(path)

        episode_match = self._find_episode(normalized)
        edition_candidates = self._find_editions(normalized)
        year = self._find_year(normalized)
        disc = self._find_disc(normalized)

        media_type = "series" if episode_match else "unknown"
        if episode_match and episode_match.special:
            media_type = "special"

        title_source = normalized
        if episode_match:
            title_source = self._remove_span(title_source, episode_match.span)

        title_source = self._remove_editions(title_source)
        title_source = self._remove_year(title_source, year)
        title_source = self.DISC_PATTERN.sub(" ", title_source)
        title = self._clean_title(title_source)

        # Bei kryptischen Dateinamen kann der unmittelbare Elternordner besser sein.
        parent_title = None
        if self._title_is_weak(title):
            for parent in parent_candidates:
                candidate = self._clean_title(self._remove_editions(self._remove_year(parent, self._find_year(parent))))
                if not self._title_is_weak(candidate):
                    parent_title = candidate
                    title = candidate
                    break

        reasons: list[str] = []
        confidence = 0.10
        if title:
            confidence += 0.30
            reasons.append("Titelkandidat aus Datei-/Ordnername")
        if parent_title:
            confidence += 0.08
            reasons.append("aussagekräftiger Elternordner")
        if episode_match:
            confidence += 0.38
            reasons.append(f"Staffel-/Folgenmuster {episode_match.pattern_name}")
        elif year and title:
            media_type = "movie"
            confidence += 0.18
            reasons.append("Filmtitel mit Jahresangabe")
        if year:
            confidence += 0.05
            reasons.append("Jahresangabe")
        if edition_candidates:
            confidence += 0.04
            reasons.append("Editionshinweis")
        if disc:
            reasons.append("Datenträger-/Teilnummer")

        season = episode_match.season if episode_match else None
        episodes = list(episode_match.episodes) if episode_match else []
        episode = episodes[0] if episodes else None

        return {
            "media_type": media_type,
            "title_candidate": title or None,
            "season": season,
            "episode": episode,
            "episodes": episodes,
            "is_multi_episode": len(episodes) > 1,
            "is_special": bool(episode_match and episode_match.special),
            "year": year,
            "edition_candidate": edition_candidates[0] if edition_candidates else None,
            "edition_candidates": edition_candidates,
            "disc_number": disc,
            "confidence": round(min(confidence, 0.97), 2),
            "reasons": reasons,
            "source_name": path.name,
            "normalized_name": normalized,
            "parent_title_candidate": parent_title,
            "requires_external_lookup": confidence < 0.85 or not title,
        }

    def _find_episode(self, value: str) -> EpisodeMatch | None:
        special = self.SPECIAL_PATTERN.search(value)
        if special:
            episode = next(int(group) for group in special.groups() if group is not None)
            return EpisodeMatch(0, (episode,), special.span(), True, "Special")

        for name, pattern in self.SERIES_PATTERNS:
            match = pattern.search(value)
            if not match:
                continue
            groups = match.groupdict()
            season_text = groups.get("season")
            first = int(groups["episode"])
            second_text = groups.get("episode2")
            episodes = (first, int(second_text)) if second_text else (first,)
            season = int(season_text) if season_text is not None else None
            return EpisodeMatch(season, episodes, match.span(), False, name)

        absolute = self.ABSOLUTE_EPISODE_PATTERN.search(value)
        if absolute:
            return EpisodeMatch(None, (int(absolute.group("episode")),), absolute.span(), False, "absolute Folge")
        return None

    @staticmethod
    def _normalize(value: str) -> str:
        value = value.replace("[", " ").replace("]", " ").replace("(", " ").replace(")", " ")
        value = re.sub(r"[._]+", " ", value)
        value = re.sub(r"\s+-\s+", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _parent_candidates(self, path: Path) -> list[str]:
        result: list[str] = []
        for parent in list(path.parents)[:3]:
            name = parent.name.strip()
            if name and name.lower() not in {"movies", "filme", "series", "serien", "video", "videos"}:
                result.append(self._normalize(name))
        return result

    @staticmethod
    def _remove_span(value: str, span: tuple[int, int]) -> str:
        return (value[: span[0]] + " " + value[span[1] :]).strip()

    def _find_year(self, value: str) -> int | None:
        matches = list(self.YEAR_PATTERN.finditer(value))
        if not matches:
            return None
        # Bei mehreren Jahreszahlen ist die letzte meist das Veröffentlichungsjahr.
        return int(matches[-1].group("year"))

    def _remove_year(self, value: str, year: int | None) -> str:
        if year is None:
            return value
        return re.sub(rf"(?<!\d){year}(?!\d)", " ", value)

    @staticmethod
    def _find_disc(value: str) -> int | None:
        match = FilenameIdentifier.DISC_PATTERN.search(value)
        return int(match.group(1)) if match else None

    @staticmethod
    def _find_editions(value: str) -> list[str]:
        editions: list[str] = []
        for pattern, label in EDITION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE) and label not in editions:
                editions.append(label)
        return editions

    @staticmethod
    def _remove_editions(value: str) -> str:
        for pattern, _label in EDITION_PATTERNS:
            value = re.sub(pattern, " ", value, flags=re.IGNORECASE)
        return value

    @staticmethod
    def _clean_title(value: str) -> str:
        value = re.sub(r"(?i)^(?:rr|proper|repack|rerip)\b", " ", value)
        tokens = re.split(r"[\s-]+", value)
        cleaned: list[str] = []
        stop_release_tail = False

        for token in tokens:
            stripped = token.strip(" -_.")
            lower = stripped.lower()
            if not stripped:
                continue
            if lower in VIDEO_NOISE_TOKENS or lower in RELEASE_PREFIXES:
                continue
            if re.fullmatch(r"\d{3,4}[pi]", lower):
                continue
            if re.fullmatch(r"(?:x|h)\.?26[45]", lower):
                continue
            if re.fullmatch(r"(?:ddp?|eac3|dts)(?:\d(?:\.\d)?)?", lower):
                continue
            if re.fullmatch(r"\d(?:\.\d)?ch", lower):
                continue
            if stop_release_tail:
                continue
            # Ein abschließender Bindestrich plus kurze Releasegruppe ist typisch.
            if (
                cleaned
                and re.fullmatch(r"[A-Z0-9]{2,8}", stripped)
                and stripped.isupper()
                and not re.fullmatch(r"[IVXLCDM]{1,8}", stripped)
            ):
                stop_release_tail = True
                continue
            cleaned.append(stripped)

        title = " ".join(cleaned)
        title = re.sub(r"\s+", " ", title).strip(" -_.")
        return title

    @staticmethod
    def _title_is_weak(title: str | None) -> bool:
        if not title:
            return True
        alpha = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ]", "", title)
        if len(alpha) < 3:
            return True
        tokens = title.split()
        return all(token.lower() in VIDEO_NOISE_TOKENS for token in tokens)
