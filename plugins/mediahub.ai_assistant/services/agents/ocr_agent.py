from __future__ import annotations
import re, subprocess, tempfile
from pathlib import Path
from typing import Any

class OCRAgent:
    def run(self,file_path:Path,ffmpeg:Path|None,tesseract:Path|None,sample_points:list[float])->dict[str,Any]:
        if ffmpeg is None: return {"state":"unavailable","reason":"ffmpeg wurde nicht gefunden."}
        if tesseract is None: return {"state":"unavailable","reason":"Tesseract ist nicht installiert."}
        findings=[]
        with tempfile.TemporaryDirectory(prefix="mediahub_ai_ocr_") as tmp:
            for idx,point in enumerate(sample_points[:6]):
                image=Path(tmp)/f"frame_{idx}.png"
                extract=[str(ffmpeg),"-hide_banner","-loglevel","error","-nostdin","-ss",str(max(0,point)),"-i",str(file_path),
                         "-frames:v","1","-vf","scale='min(1920,iw)':-2","-y",str(image)]
                try:
                    ep=subprocess.run(extract,capture_output=True,timeout=25,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    if ep.returncode!=0 or not image.exists(): continue
                    op=subprocess.run([str(tesseract),str(image),"stdout","-l","deu+eng","--psm","11"],capture_output=True,text=True,
                                      encoding="utf-8",errors="replace",timeout=30,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    text=re.sub(r"\s+"," ",op.stdout or "").strip()
                    if len(text)>=3: findings.append({"second":round(float(point),2),"text":text[:500]})
                except Exception as exc: findings.append({"second":round(float(point),2),"error":str(exc)})
        combined=" ".join(f.get("text","") for f in findings)
        episode_patterns=re.findall(r"\b(?:S\d{1,2}E\d{1,3}|Staffel\s*\d+|Episode\s*\d+|Folge\s*\d+)\b",combined,re.I)
        return {"state":"completed" if findings else "no_text","findings":findings,"episode_hints":episode_patterns[:10]}
