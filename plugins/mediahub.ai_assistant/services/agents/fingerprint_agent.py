from __future__ import annotations
import hashlib, subprocess
from pathlib import Path
from typing import Any

class FingerprintAgent:
    """Erzeugt reproduzierbare, kompakte Analyse-Fingerprints ohne Mediendateien zu verändern."""
    def run(self,file_path:Path,ffmpeg:Path|None,duration:float)->dict[str,Any]:
        if ffmpeg is None: return {"state":"unavailable","reason":"ffmpeg wurde nicht gefunden."}
        points=[max(0,duration*x) for x in (0.1,0.3,0.5,0.7,0.9)] if duration else [10,30,60]
        chunks=[]
        for pnt in points:
            cmd=[str(ffmpeg),"-hide_banner","-loglevel","error","-nostdin","-ss",str(round(pnt,2)),"-i",str(file_path),
                 "-frames:v","1","-vf","scale=32:32,format=gray","-f","rawvideo","-"]
            try:
                p=subprocess.run(cmd,capture_output=True,timeout=20,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if p.returncode==0 and p.stdout: chunks.append(p.stdout)
            except Exception: pass
        if not chunks: return {"state":"failed","reason":"Keine Fingerprint-Stichprobe erzeugt."}
        digest=hashlib.sha256(b"".join(chunks)).hexdigest()
        return {"state":"completed","algorithm":"sha256-of-5-normalized-gray-frames-v1","video_fingerprint":digest,"sample_count":len(chunks)}
