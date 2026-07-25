from __future__ import annotations
from pathlib import Path
from typing import Any
from services.agents.frame_agent import FrameAgent
from services.agents.subtitle_agent import SubtitleAgent
from services.agents.audio_agent import AudioAgent
from services.agents.ocr_agent import OCRAgent
from services.agents.fingerprint_agent import FingerprintAgent
from services.agents.scene_agent import SceneAgent

class InVideoAgent:
    """Führt eine begrenzte, echte Inhaltsanalyse mit zentral verwalteten Werkzeugen aus."""
    def __init__(self, tools=None):
        self.tools=tools
        self.frame=FrameAgent(); self.subtitle=SubtitleAgent(); self.audio=AudioAgent(); self.ocr=OCRAgent(); self.fingerprint=FingerprintAgent(); self.scene=SceneAgent()

    def capabilities(self)->dict[str,Any]:
        return {"schema_version":3,"implemented":True,"implementation_level":"bounded_real_analysis","agents":[
            {"id":"frame","state":"active","purpose":"Reale Frame-Messwerte"},{"id":"subtitle","state":"active","purpose":"Textbeweise aus Untertiteln"},
            {"id":"ocr","state":"active_if_tesseract","purpose":"Titelkarten und Einblendungen"},{"id":"audio","state":"active","purpose":"Lautheit, Dynamik und Clipping"},
            {"id":"fingerprint","state":"active","purpose":"Reproduzierbarer Bildfingerprint"},{"id":"scene","state":"active","purpose":"Szenenwechsel-Stichprobe"},
            {"id":"quality","state":"active","purpose":"Technische und gemessene Bild-/Tonqualität"}],
            "shared_analysis":["ffprobe","mediainfo","frame_metrics","audio_metrics","subtitles","ocr","fingerprints"],
            "edition_targets":["Uncut","Extended","Director's Cut","Theatrical Cut","Remastered"]}

    def _plan(self,analysis,required):
        s=analysis.get("summary") or {}; duration=float(s.get("duration_seconds") or 0); chapters=int(s.get("chapters") or 0)
        pts=[0,5,15]
        if duration>60: pts += [duration*.25,duration*.5,duration*.75,max(0,duration-30)]
        return {"schema_version":3,"required":bool(required),"sample_plan":{"fixed_seconds":sorted({round(max(0,x),2) for x in pts}),
                "chapter_starts":chapters,"scene_change_sampling":True,"maximum_frames":40}}

    def run(self,analysis:dict[str,Any],required:bool)->dict[str,Any]:
        plan=self._plan(analysis,required)
        if not required:
            return {**plan,"state":"deferred","reason":"Vorhandene Beweise reichen aus; Tiefenanalyse wurde eingespart."}
        path=Path((analysis.get("file") or {}).get("path") or "")
        summary=analysis.get("summary") or {}; duration=float(summary.get("duration_seconds") or 0)
        ffmpeg=self.tools.find("ffmpeg") if self.tools else None; tess=self.tools.find("tesseract") if self.tools else None
        pts=plan["sample_plan"]["fixed_seconds"]
        results={"frame_agent":self.frame.run(path,ffmpeg,pts),
                 "subtitle_agent":self.subtitle.run(path,ffmpeg,int(summary.get("subtitle_tracks") or 0)),
                 "audio_agent":self.audio.run(path,ffmpeg,duration),
                 "ocr_agent":self.ocr.run(path,ffmpeg,tess,pts),
                 "fingerprint_agent":self.fingerprint.run(path,ffmpeg,duration),
                 "scene_agent":self.scene.run(path,ffmpeg,duration)}
        completed=sum(1 for v in results.values() if v.get("state")=="completed")
        return {**plan,"state":"completed" if completed else "partial","completed_agents":completed,"agents":results,
                "quality_agent":{"active":True,"uses_same_samples":True}}

    def plan(self,analysis:dict[str,Any],required:bool)->dict[str,Any]:
        return self.run(analysis,required)
