from __future__ import annotations
import re, subprocess
from pathlib import Path
from typing import Any

class SceneAgent:
    def run(self,file_path:Path,ffmpeg:Path|None,duration:float)->dict[str,Any]:
        if ffmpeg is None: return {"state":"unavailable","reason":"ffmpeg wurde nicht gefunden."}
        limit=min(max(duration,0),600) or 600
        cmd=[str(ffmpeg),"-hide_banner","-nostdin","-i",str(file_path),"-t",str(round(limit,2)),"-vf",
             "select='gt(scene,0.40)',showinfo","-an","-f","null","-"]
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=70,check=False,
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            times=[float(v) for v in re.findall(r"pts_time:([0-9.]+)",p.stderr or "")]
            return {"state":"completed","analyzed_seconds":round(limit,2),"scene_changes":len(times),"first_scene_changes":times[:30]}
        except Exception as exc: return {"state":"failed","reason":str(exc)}
