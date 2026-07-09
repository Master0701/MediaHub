import json
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, default: Any) -> Any:
        if not self.path.exists():
            self.save(default)
            return default

        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(self, data: Any) -> None:
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)