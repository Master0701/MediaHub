from __future__ import annotations
import re, subprocess
from collections import Counter
from pathlib import Path
from typing import Any

class SubtitleAgent:
    STOP={"aber","oder","und","der","die","das","ein","eine","ist","sind","ich","du","wir","sie","nicht","mit","von","auf","für","the","and","that","this","you","are","was","have","not","with","from"}
    def run(self,file_path:Path,ffmpeg:Path|None,available_tracks:int)->dict[str,Any]:
        if available_tracks<=0: return {"state":"not_applicable","reason":"Keine Untertitelspur vorhanden."}
        if ffmpeg is None: return {"state":"unavailable","reason":"ffmpeg wurde nicht gefunden."}
        cmd=[str(ffmpeg),"-hide_banner","-nostdin","-i",str(file_path),"-map","0:s:0","-t","600","-f","srt","-"]
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=45,check=False,
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if p.returncode!=0 or not p.stdout.strip():
                return {"state":"unsupported","reason":"Die erste Untertitelspur konnte nicht als Text extrahiert werden."}
            clean=re.sub(r"<[^>]+>|\{\\.*?\}|\d+\s*\n|\d\d:\d\d:.*?--.*?\n"," ",p.stdout,flags=re.S)
            words=[w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß'-]{3,}",clean)]
            keywords=[w for w,_ in Counter(w for w in words if w not in self.STOP).most_common(25)]
            proper=[]
            for token in re.findall(r"\b[A-ZÄÖÜ][a-zäöüß]{2,}\b",clean):
                if token.lower() not in self.STOP and token not in proper: proper.append(token)
            return {"state":"completed","characters":len(p.stdout),"keywords":keywords,"proper_names":proper[:20],
                    "text_preview":re.sub(r"\s+"," ",clean).strip()[:500]}
        except Exception as exc: return {"state":"failed","reason":str(exc)}
