from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class ToolResolver:
    """Findet gemeinsam verwaltete MediaHub-Werkzeuge ohne Plugin-Kopien."""

    def __init__(self, mediahub_base: Path):
        self.mediahub_base = Path(mediahub_base)
        self.tools_dir = self.mediahub_base / "tools"

    def _candidates(self, names: Iterable[str]) -> list[Path]:
        result: list[Path] = []
        for name in names:
            result.append(self.tools_dir / name)
            result.append(self.tools_dir / name.lower())
            result.append(self.tools_dir / name.upper())
        return result

    def find(self, tool_id: str) -> Path | None:
        mapping = {
            "ffprobe": ("ffprobe.exe", "ffprobe"),
            "mediainfo": ("mediainfo.exe", "MediaInfo.exe", "mediainfo"),
            "tesseract": ("tesseract.exe", "tesseract"),
            "mkvmerge": ("mkvmerge.exe", "mkvmerge"),
            "mkvpropedit": ("mkvpropedit.exe", "mkvpropedit"),
        }
        names = mapping.get(tool_id, (f"{tool_id}.exe", tool_id))

        for path in self._candidates(names):
            if path.is_file():
                return path.resolve()

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
            "tools_dir": str(self.tools_dir),
            "ffprobe": self._entry("ffprobe", required=True),
            "mediainfo": self._entry("mediainfo", required=True),
            "tesseract": self._entry("tesseract", required=False),
            "mkvmerge": self._entry("mkvmerge", required=False),
            "mkvpropedit": self._entry("mkvpropedit", required=False),
        }

    def _entry(self, tool_id: str, required: bool) -> dict:
        path = self.find(tool_id)
        return {
            "id": tool_id,
            "required": required,
            "installed": path is not None,
            "path": str(path) if path else None,
        }
