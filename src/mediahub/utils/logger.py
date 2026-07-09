from datetime import datetime
from pathlib import Path


class AppLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def _write(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {level}: {message}\n"

        with self.log_file.open("a", encoding="utf-8") as file:
            file.write(line)