from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from services.tool_resolver import ToolResolver
from services.filename_identifier import FilenameIdentifier
from services.analysis_cache import AnalysisCache


VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".m4v", ".ts", ".m2ts",
    ".webm", ".wmv", ".mpg", ".mpeg"
}


class MediaAnalyzer:
    """Schnelle technische Analyse mit MediaInfo, ffprobe und Cache."""

    def __init__(
        self,
        mediahub_base: Path,
        knowledge_database_path: Path | None = None,
    ):
        self.tools = ToolResolver(mediahub_base)
        self.filename_identifier = FilenameIdentifier()
        self.cache = (
            AnalysisCache(knowledge_database_path)
            if knowledge_database_path is not None
            else None
        )


    def analyze(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Nicht unterstützte Videodatei: {path.suffix}")

        if self.cache is not None:
            cached = self.cache.get(path)
            if cached is not None:
                return cached

        result: dict[str, Any] = {
            "file": {
                "path": str(path.resolve()),
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "extension": path.suffix.lower(),
            },
            "mediainfo": None,
            "ffprobe": None,
            "summary": {},
            "warnings": [],
            "methods_used": ["filename"],
            "cache": {"hit": False, "message": "Neue Analyse durchgeführt."},
            "identification": self.filename_identifier.identify(path),
        }

        mediainfo = self.tools.find("mediainfo")
        if mediainfo:
            try:
                result["mediainfo"] = self._run_json(
                    [str(mediainfo), "--Output=JSON", str(path)]
                )
                result["methods_used"].append("mediainfo")
            except Exception as exc:
                result["warnings"].append(f"MediaInfo fehlgeschlagen: {exc}")
        else:
            result["warnings"].append(
                "MediaInfo ist noch nicht installiert; ffprobe-Fallback wird verwendet."
            )

        ffprobe = self.tools.find("ffprobe")
        if ffprobe:
            try:
                result["ffprobe"] = self._run_json([
                    str(ffprobe),
                    "-v", "error",
                    "-show_format",
                    "-show_streams",
                    "-show_chapters",
                    "-of", "json",
                    str(path),
                ])
                result["methods_used"].append("ffprobe")
            except Exception as exc:
                result["warnings"].append(f"ffprobe fehlgeschlagen: {exc}")
        else:
            result["warnings"].append("ffprobe wurde nicht gefunden.")

        result["summary"] = self._build_summary(result)
        result["evidence"] = self._build_evidence(result)
        if self.cache is not None:
            self.cache.put(path, result)
        return result

    @staticmethod
    def _run_json(command: list[str]) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or f"Exit-Code {completed.returncode}")
        return json.loads(completed.stdout)


    @staticmethod
    def _mediainfo_tracks(result: dict[str, Any]) -> list[dict[str, Any]]:
        media = result.get("mediainfo") or {}
        tracks = ((media.get("media") or {}).get("track") or [])
        return tracks if isinstance(tracks, list) else []

    @classmethod
    def _build_evidence(cls, result: dict[str, Any]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        identification = result.get("identification") or {}
        if identification.get("title_candidate"):
            evidence.append({
                "source": "Dateiname",
                "status": "Hinweis",
                "detail": identification.get("title_candidate"),
            })
        if result.get("ffprobe"):
            evidence.append({
                "source": "ffprobe",
                "status": "Bestätigt",
                "detail": "Container, Streams, Kapitel und Laufzeit gelesen",
            })
        if result.get("mediainfo"):
            evidence.append({
                "source": "MediaInfo",
                "status": "Bestätigt",
                "detail": "Zusätzliche Container-, HDR-, Audio- und Tag-Daten gelesen",
            })
        else:
            evidence.append({
                "source": "MediaInfo",
                "status": "Fehlt",
                "detail": "Wird nach zentraler Tool-Installation automatisch ergänzt",
            })
        return evidence

    @staticmethod
    def _build_summary(result: dict[str, Any]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "duration_seconds": None,
            "container": None,
            "video_codec": None,
            "width": None,
            "height": None,
            "audio_tracks": 0,
            "subtitle_tracks": 0,
            "chapters": 0,
            "title_tags": [],
        }

        probe = result.get("ffprobe") or {}
        fmt = probe.get("format") or {}
        streams = probe.get("streams") or []
        chapters = probe.get("chapters") or []

        try:
            summary["duration_seconds"] = round(float(fmt.get("duration")), 3)
        except (TypeError, ValueError):
            pass

        summary["container"] = fmt.get("format_long_name") or fmt.get("format_name")
        summary["chapters"] = len(chapters)

        for stream in streams:
            kind = stream.get("codec_type")
            if kind == "video" and summary["video_codec"] is None:
                summary["video_codec"] = stream.get("codec_long_name") or stream.get("codec_name")
                summary["width"] = stream.get("width")
                summary["height"] = stream.get("height")
            elif kind == "audio":
                summary["audio_tracks"] += 1
            elif kind == "subtitle":
                summary["subtitle_tracks"] += 1

            tags = stream.get("tags") or {}
            for key in ("title", "handler_name"):
                value = tags.get(key)
                if value and value not in summary["title_tags"]:
                    summary["title_tags"].append(value)

        format_tags = fmt.get("tags") or {}
        for key in ("title", "show", "episode_id", "comment"):
            value = format_tags.get(key)
            if value and value not in summary["title_tags"]:
                summary["title_tags"].append(value)


        for track in MediaAnalyzer._mediainfo_tracks(result):
            track_type = str(track.get("@type") or "").lower()
            if track_type == "general":
                if not summary["duration_seconds"]:
                    try:
                        summary["duration_seconds"] = round(float(track.get("Duration")), 3)
                    except (TypeError, ValueError):
                        pass
                summary["container"] = (
                    summary["container"]
                    or track.get("Format")
                    or track.get("Format_Commercial")
                )
            elif track_type == "video":
                summary["video_codec"] = (
                    summary["video_codec"]
                    or track.get("Format_Commercial_IfAny")
                    or track.get("Format")
                )
                summary["width"] = summary["width"] or track.get("Width")
                summary["height"] = summary["height"] or track.get("Height")
                summary["hdr_format"] = (
                    track.get("HDR_Format")
                    or track.get("HDR_Format_Commercial")
                    or track.get("HDR_Format_String")
                )
            elif track_type == "audio":
                summary["mediainfo_audio_tracks"] = (
                    summary.get("mediainfo_audio_tracks", 0) + 1
                )
            elif track_type == "text":
                summary["mediainfo_subtitle_tracks"] = (
                    summary.get("mediainfo_subtitle_tracks", 0) + 1
                )

        return summary
