from __future__ import annotations
import re, subprocess
from pathlib import Path
from typing import Any

class AudioAgent:
    def run(self,file_path:Path,ffmpeg:Path|None,duration:float)->dict[str,Any]:
        if ffmpeg is None: return {"state":"unavailable","reason":"ffmpeg wurde nicht gefunden."}
        start=max(0.0,(duration-90.0)/2.0)
        cmd=[str(ffmpeg),"-hide_banner","-nostdin","-ss",str(round(start,2)),"-i",str(file_path),"-t","90","-vn",
             "-af","volumedetect,astats=metadata=0:reset=0","-f","null","-"]
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=50,check=False,
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            t=(p.stdout or "")+"\n"+(p.stderr or "")
            def num(pattern):
                m=re.search(pattern,t,re.I); return float(m.group(1)) if m else None
            metrics={"mean_volume_db":num(r"mean_volume:\s*(-?[0-9.]+) dB"),"max_volume_db":num(r"max_volume:\s*(-?[0-9.]+) dB"),
                     "peak_level_db":num(r"Peak level dB:\s*(-?[0-9.]+|inf)"),"rms_level_db":num(r"RMS level dB:\s*(-?[0-9.]+|inf)"),
                     "dynamic_range_db":num(r"Dynamic range:\s*([0-9.]+)"),"zero_crossings_rate":num(r"Zero crossings rate:\s*([0-9.]+)")}
            metrics={k:v for k,v in metrics.items() if v is not None}
            maxv=metrics.get("max_volume_db")
            clipping_risk=maxv is not None and maxv>-0.1
            return {"state":"completed" if metrics else "failed","sample_start":round(start,2),"sample_duration":90,
                    "metrics":metrics,"clipping_risk":clipping_risk}
        except Exception as exc: return {"state":"failed","reason":str(exc)}
