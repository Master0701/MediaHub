from __future__ import annotations

import json
import sys
from pathlib import Path


class HelpLoader:
    """Lädt den erzeugten help_index.json."""

    def __init__(self, base_dir=None):
        self._explicit_base_dir = base_dir is not None
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()

    def runtime_root(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent

        return Path(__file__).resolve().parents[3]

    def meipass_root(self) -> Path | None:
        value = getattr(sys, "_MEIPASS", None)
        if value:
            return Path(value)

        return None

    def candidate_dirs(self) -> list[Path]:
        folders = []

        meipass = self.meipass_root()
        if meipass:
            folders.append(meipass / "assets" / "docs")

        folders.append(self.base_dir / "assets" / "docs")

        # Bei einem ausdrücklich übergebenen Basisordner (z. B. Tests oder
        # ein portables Datenverzeichnis) darf nicht still auf die
        # Projektdokumentation zurückgefallen werden.
        if not self._explicit_base_dir:
            folders.append(self.runtime_root() / "assets" / "docs")

        return folders

    def index_file(self) -> Path | None:
        for folder in self.candidate_dirs():
            file = folder / "help_index.json"

            if file.exists():
                return file

        return None

    def load(self) -> list[dict]:
        file = self.index_file()

        if file is None:
            return []

        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            return []
        
    def first_existing_doc(self, relative_path: str) -> Path | None:
        for folder in self.candidate_dirs():
            path = folder / relative_path

            if path.exists():
                return path

        return None