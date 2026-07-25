from __future__ import annotations
import re, subprocess
from pathlib import Path
from typing import Any

class FrameAgent:
    """Liest reale Bildmesswerte aus gezielten FFmpeg-Stichproben."""
    KEYS = {"YAVG", "YMIN", "YMAX", "SATAVG", "SATMAX"}

    def run(self, file_path: Path, ffmpeg: Path | None, sample_points: list[float]) -> dict[str, Any]:
        if ffmpeg is None:
            return {"state": "unavailable", "reason": "ffmpeg wurde nicht gefunden.", "samples": []}
        samples=[]
        for point in sample_points[:10]:
            cmd=[str(ffmpeg), "-hide_banner", "-nostdin", "-ss", str(max(0, point)), "-i", str(file_path),
                 "-frames:v", "1", "-vf", "signalstats,metadata=print", "-an", "-f", "null", "-"]
            try:
                p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=25,check=False,
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                text=(p.stdout or "")+"\n"+(p.stderr or "")
                metrics={}
                for key,val in re.findall(r"lavfi\.signalstats\.([A-Z0-9]+)=(-?[0-9.]+)", text):
                    if key in self.KEYS:
                        metrics[key.lower()]=round(float(val),3)
                if metrics:
                    samples.append({"second": round(float(point),2), "metrics": metrics})
            except Exception as exc:
                samples.append({"second": round(float(point),2), "error": str(exc)})
        good=[s for s in samples if s.get("metrics")]
        avg={}
        for key in ("yavg","ymin","ymax","satavg","satmax"):
            vals=[s["metrics"][key] for s in good if key in s["metrics"]]
            if vals: avg[key]=round(sum(vals)/len(vals),3)
        return {"state": "completed" if good else "failed", "sample_count": len(good), "samples": samples, "averages": avg,
                "purpose": "Helligkeit, Kontrastumfang und Farbsättigung realer Videoframes"}
