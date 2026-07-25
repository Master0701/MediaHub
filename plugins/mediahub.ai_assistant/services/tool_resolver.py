from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class ToolResolver:
    """Findet zentral verwaltete MediaHub-Werkzeuge ohne Plugin-Kopien."""

    def __init__(self, mediahub_base: Path):
        self.mediahub_base = Path(mediahub_base).resolve()
        self.search_roots = self._build_search_roots()

    def _build_search_roots(self) -> list[Path]:
        roots = [
            self.mediahub_base / "tools",
            self.mediahub_base / "MediaHub_Tools",
            self.mediahub_base.parent / "MediaHub_Tools",
            self.mediahub_base.parent / "tools",
        ]
        env_root = os.environ.get("MEDIAHUB_TOOLS_DIR")
        if env_root:
            roots.insert(0, Path(env_root))
        result=[]
        seen=set()
        for root in roots:
            key=str(root.resolve()).lower()
            if key not in seen:
                seen.add(key); result.append(root)
        return result

    @staticmethod
    def _names(tool_id: str) -> tuple[str, ...]:
        mapping = {
            "ffprobe": ("ffprobe.exe", "ffprobe"),
            "ffmpeg": ("ffmpeg.exe", "ffmpeg"),
            "mediainfo": ("mediainfo.exe", "MediaInfo.exe", "mediainfo"),
            "tesseract": ("tesseract.exe", "tesseract"),
            "mkvmerge": ("mkvmerge.exe", "mkvmerge"),
            "mkvpropedit": ("mkvpropedit.exe", "mkvpropedit"),
        }
        return mapping.get(tool_id, (f"{tool_id}.exe", tool_id))

    def find(self, tool_id: str) -> Path | None:
        names = self._names(tool_id)
        for root in self.search_roots:
            if not root.exists():
                continue
            for name in names:
                direct = root / name
                if direct.is_file():
                    return direct.resolve()
            for name in names:
                matches = list(root.glob(f"**/{name}"))
                if matches:
                    return matches[0].resolve()
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory:
                continue
            base = Path(directory)
            for name in names:
                path = base / name
                if path.is_file():
                    return path.resolve()
        return None

    def status(self) -> dict:
        return {
            "search_roots": [str(p) for p in self.search_roots],
            "ffprobe": self._entry("ffprobe", True),
            "ffmpeg": self._entry("ffmpeg", True),
            "mediainfo": self._entry("mediainfo", True),
            "tesseract": self._entry("tesseract", False),
            "mkvmerge": self._entry("mkvmerge", False),
            "mkvpropedit": self._entry("mkvpropedit", False),
        }

    def _entry(self, tool_id: str, required: bool) -> dict:
        path = self.find(tool_id)
        return {"id": tool_id, "required": required, "installed": path is not None,
                "path": str(path) if path else None}
