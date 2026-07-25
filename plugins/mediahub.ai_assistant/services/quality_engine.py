from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class QualityThresholds:
    excellent: int = 85
    good: int = 70
    acceptable: int = 55
    replace: int = 40


class QualityProfileStore:
    """Speichert persönliche Mindestqualitäts-Referenzen lokal im Plugin-Datenbereich."""

    def __init__(self, database_path: Path | None):
        self.path = None
        if database_path is not None:
            self.path = Path(database_path).with_name("ai_quality_profiles.json")

    def load(self) -> dict[str, Any]:
        if self.path is None or not self.path.exists():
            return {"schema_version": 1, "active_profile": None, "profiles": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("schema_version", 1)
                data.setdefault("active_profile", None)
                data.setdefault("profiles", {})
                return data
        except Exception:
            pass
        return {"schema_version": 1, "active_profile": None, "profiles": {}}

    def save_reference(self, name: str, quality: dict[str, Any], activate: bool = True) -> dict[str, Any]:
        if self.path is None:
            raise RuntimeError("Kein Speicherpfad für Qualitätsprofile verfügbar.")
        data = self.load()
        profile = {
            "name": name,
            "video_score": int((quality.get("video") or {}).get("score") or 0),
            "audio_score": int((quality.get("audio") or {}).get("score") or 0),
            "overall_score": int(quality.get("overall_score") or 0),
            "source_metrics": quality.get("metrics") or {},
        }
        data["profiles"][name] = profile
        if activate:
            data["active_profile"] = name
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return profile


class QualityEngine:
    """Technische Startbewertung für sichtbare und hörbare Medienqualität.

    v0.8.0 bildet eine reproduzierbare Basis. Spätere Agenten ergänzen reale
    Frame-, Audio-, OCR- und Fingerprint-Messwerte, ohne das Datenformat zu ändern.
    """

    def __init__(self, profile_store: QualityProfileStore | None = None):
        self.thresholds = QualityThresholds()
        self.profile_store = profile_store

    def evaluate(self, analysis: dict[str, Any]) -> dict[str, Any]:
        summary = analysis.get("summary") or {}
        probe = analysis.get("ffprobe") or {}
        streams = probe.get("streams") or []
        fmt = probe.get("format") or {}

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        audio_stream = audio_streams[0] if audio_streams else {}

        video_score, video_reasons, video_metrics = self._video_score(video_stream, fmt, summary)
        audio_score, audio_reasons, audio_metrics = self._audio_score(audio_stream, audio_streams)
        video_score, measured_video = self._apply_frame_measurements(analysis, video_score)
        audio_score, measured_audio = self._apply_audio_measurements(analysis, audio_score)
        video_reasons.extend(measured_video)
        audio_reasons.extend(measured_audio)

        has_audio = bool(audio_streams)
        overall = round(video_score * 0.7 + audio_score * 0.3) if has_audio else video_score
        status = self._status(overall)

        result = {
            "schema_version": 2,
            "implemented": True,
            "mode": "technical_and_measured_samples",
            "video": {
                "score": video_score,
                "status": self._status(video_score),
                "reasons": video_reasons,
            },
            "audio": {
                "score": audio_score if has_audio else None,
                "status": self._status(audio_score) if has_audio else "not_available",
                "reasons": audio_reasons if has_audio else ["Keine Tonspur erkannt."],
            },
            "overall_score": overall,
            "status": status,
            "label": self._label(status),
            "metrics": {"video": video_metrics, "audio": audio_metrics},
            "reference_comparison": self._compare_reference(overall, video_score, audio_score),
            "recommendation": self._recommendation(status, video_score, audio_score, has_audio),
            "limitations": [
                "Frame- und Audiostichproben ergänzen die technische Basisbewertung, ersetzen aber noch keine vollständige subjektive Sicht- und Hörprüfung.",
                "Auflösung und Bitrate allein entscheiden nicht über die endgültige Qualität.",
            ],
        }
        return result

    def save_reference(self, name: str, quality: dict[str, Any], activate: bool = True) -> dict[str, Any]:
        if self.profile_store is None:
            raise RuntimeError("Qualitätsprofile sind nicht konfiguriert.")
        return self.profile_store.save_reference(name, quality, activate=activate)

    @staticmethod
    def _int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _video_score(self, stream: dict[str, Any], fmt: dict[str, Any], summary: dict[str, Any]):
        width = self._int(stream.get("width") or summary.get("width"))
        height = self._int(stream.get("height") or summary.get("height"))
        bitrate = self._int(stream.get("bit_rate"))
        if not bitrate:
            bitrate = self._int(fmt.get("bit_rate"))
        codec = str(stream.get("codec_name") or "").lower()
        pix_fmt = str(stream.get("pix_fmt") or "").lower()
        field_order = str(stream.get("field_order") or "").lower()
        bit_depth = self._int(stream.get("bits_per_raw_sample"), 8)

        if height >= 2160: resolution = 38
        elif height >= 1440: resolution = 34
        elif height >= 1080: resolution = 30
        elif height >= 720: resolution = 23
        elif height >= 576: resolution = 17
        elif height >= 480: resolution = 13
        else: resolution = 8

        pixels = max(width * height, 1)
        bpp_proxy = bitrate / pixels if bitrate else 0
        if bpp_proxy >= 8: compression = 32
        elif bpp_proxy >= 4: compression = 28
        elif bpp_proxy >= 2: compression = 23
        elif bpp_proxy >= 1: compression = 17
        elif bpp_proxy > 0: compression = 11
        else: compression = 8

        codec_points = 16 if codec in {"hevc", "h265", "av1", "vp9"} else 13 if codec in {"h264", "avc1"} else 10
        depth_points = 8 if bit_depth >= 10 or "10" in pix_fmt else 5
        scan_points = 6 if field_order in {"progressive", "unknown", ""} else 2
        score = max(0, min(100, resolution + compression + codec_points + depth_points + scan_points))

        reasons = [f"Auflösung {width} × {height}."]
        reasons.append(f"Videocodec {codec or 'unbekannt'}.")
        if bitrate:
            reasons.append(f"Ermittelte Video-/Gesamtbitrate ungefähr {round(bitrate / 1_000_000, 2)} Mbit/s.")
        if field_order and field_order not in {"progressive", "unknown"}:
            reasons.append("Interlaced-/Halbbild-Hinweis senkt die technische Bewertung.")
        return score, reasons, {"width": width, "height": height, "bitrate": bitrate, "codec": codec, "bit_depth": bit_depth, "field_order": field_order}

    def _audio_score(self, stream: dict[str, Any], all_streams: list[dict[str, Any]]):
        codec = str(stream.get("codec_name") or "").lower()
        bitrate = self._int(stream.get("bit_rate"))
        channels = self._int(stream.get("channels"))
        sample_rate = self._int(stream.get("sample_rate"))
        lossless = codec in {"flac", "alac", "truehd", "mlp", "dts_hd_ma"}

        codec_points = 35 if lossless else 29 if codec in {"eac3", "dts", "ac3", "aac", "opus"} else 20
        if bitrate >= 1_500_000: bitrate_points = 30
        elif bitrate >= 768_000: bitrate_points = 26
        elif bitrate >= 384_000: bitrate_points = 22
        elif bitrate >= 192_000: bitrate_points = 17
        elif bitrate > 0: bitrate_points = 11
        else: bitrate_points = 8
        channel_points = 20 if channels >= 8 else 17 if channels >= 6 else 13 if channels >= 2 else 8
        sample_points = 10 if sample_rate >= 96000 else 8 if sample_rate >= 48000 else 5
        language_bonus = min(5, max(0, len(all_streams) - 1) * 2)
        score = max(0, min(100, codec_points + bitrate_points + channel_points + sample_points + language_bonus))

        reasons = [f"Audiocodec {codec or 'unbekannt'}, {channels or '?'} Kanäle, {sample_rate or '?'} Hz."]
        if bitrate:
            reasons.append(f"Audiobitrate ungefähr {round(bitrate / 1000)} kbit/s.")
        if len(all_streams) > 1:
            reasons.append(f"{len(all_streams)} Tonspuren erhöhen den Nutzwert der Datei.")
        return score, reasons, {"codec": codec, "bitrate": bitrate, "channels": channels, "sample_rate": sample_rate, "track_count": len(all_streams), "lossless": lossless}

    @staticmethod
    def _apply_frame_measurements(analysis: dict[str, Any], score: int) -> tuple[int, list[str]]:
        data = ((((analysis.get("in_video") or {}).get("agents") or {}).get("frame_agent") or {}))
        avg = data.get("averages") or {}
        if not avg: return score, []
        yavg=float(avg.get("yavg") or 0); spread=float(avg.get("ymax") or 0)-float(avg.get("ymin") or 0)
        adjustment=0; reasons=[]
        if yavg < 25: adjustment-=8; reasons.append("Gemessene Frames sind überwiegend sehr dunkel.")
        elif yavg > 225: adjustment-=7; reasons.append("Gemessene Frames sind überwiegend sehr hell.")
        else: adjustment+=3; reasons.append("Gemessene Helligkeit liegt in einem brauchbaren Bereich.")
        if spread < 80: adjustment-=6; reasons.append("Der gemessene Kontrastumfang ist niedrig.")
        elif spread > 180: adjustment+=3; reasons.append("Der gemessene Kontrastumfang ist gut.")
        return max(0,min(100,score+adjustment)), reasons

    @staticmethod
    def _apply_audio_measurements(analysis: dict[str, Any], score: int) -> tuple[int, list[str]]:
        data = ((((analysis.get("in_video") or {}).get("agents") or {}).get("audio_agent") or {}))
        metrics=data.get("metrics") or {}
        if not metrics: return score, []
        adjustment=0; reasons=[]; mean=metrics.get("mean_volume_db"); maxv=metrics.get("max_volume_db"); dyn=metrics.get("dynamic_range_db")
        if data.get("clipping_risk"): adjustment-=10; reasons.append("Die Audiostichprobe zeigt ein mögliches Clipping-Risiko.")
        elif maxv is not None: adjustment+=2; reasons.append(f"Gemessene Spitzenlautstärke {maxv:.1f} dB.")
        if mean is not None and mean < -35: adjustment-=5; reasons.append("Die Audiostichprobe ist ungewöhnlich leise.")
        if dyn is not None and dyn < 5: adjustment-=5; reasons.append("Die gemessene Audiodynamik ist gering.")
        elif dyn is not None and dyn >= 10: adjustment+=3; reasons.append("Die gemessene Audiodynamik ist gut.")
        return max(0,min(100,score+adjustment)), reasons

    def _status(self, score: int) -> str:
        if score >= self.thresholds.excellent: return "excellent"
        if score >= self.thresholds.good: return "good"
        if score >= self.thresholds.acceptable: return "acceptable"
        if score >= self.thresholds.replace: return "improve_recommended"
        return "replace_recommended"

    @staticmethod
    def _label(status: str) -> str:
        return {
            "excellent": "sehr gut",
            "good": "gut",
            "acceptable": "noch akzeptabel",
            "improve_recommended": "verbesserungswürdig",
            "replace_recommended": "neu in besserer Qualität suchen",
        }.get(status, status)

    def _compare_reference(self, overall: int, video: int, audio: int) -> dict[str, Any]:
        if self.profile_store is None:
            return {"available": False, "reason": "Kein Profilspeicher konfiguriert."}
        data = self.profile_store.load()
        name = data.get("active_profile")
        profile = (data.get("profiles") or {}).get(name) if name else None
        if not profile:
            return {"available": False, "reason": "Noch keine persönliche Mindestqualität festgelegt."}
        delta = overall - int(profile.get("overall_score") or 0)
        return {
            "available": True,
            "profile": name,
            "delta": delta,
            "meets_reference": delta >= 0,
            "video_delta": video - int(profile.get("video_score") or 0),
            "audio_delta": audio - int(profile.get("audio_score") or 0),
        }

    def _recommendation(self, status: str, video: int, audio: int, has_audio: bool) -> dict[str, Any]:
        focus = "both"
        if has_audio and abs(video - audio) >= 12:
            focus = "video" if video < audio else "audio"
        action = {
            "excellent": "keep",
            "good": "keep",
            "acceptable": "keep_with_marker",
            "improve_recommended": "search_upgrade",
            "replace_recommended": "replace_priority",
        }[status]
        return {"action": action, "focus": focus, "automatic_change": False, "review_required": True}
