import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from src.mediahub.controllers.channel_controller import ChannelController
from src.mediahub.gui.main_window import MainWindow
from src.mediahub.storage.repository import MediaRepository
from src.mediahub.utils.logger import AppLogger


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[2]


def ensure_app_folders(base_dir: Path) -> None:
    folders = [
        "config",
        "tools",
        "downloads",
        "logs",
        "archive",
        "cache",
    ]

    for folder in folders:
        (base_dir / folder).mkdir(parents=True, exist_ok=True)


def main():
    app = QApplication(sys.argv)

    base_dir = get_base_dir()

    try:
        ensure_app_folders(base_dir)

        logger = AppLogger(base_dir / "logs")

        repository = MediaRepository(base_dir, logger=logger)
        repository.initialize()

        channel_controller = ChannelController(
            base_dir / "config",
            logger=logger,
            repository=repository,
        )

        window = MainWindow(channel_controller, logger, repository=repository)
        window.show()

        logger.info("MediaHub gestartet")
        sys.exit(app.exec())

    except Exception as error:
        QMessageBox.critical(
            None,
            "MediaHub Startfehler",
            f"MediaHub konnte nicht gestartet werden.\n\n"
            f"Fehler:\n{error}\n\n"
            f"Programmordner:\n{base_dir}\n\n"
            f"Hinweis:\n"
            f"Wenn MediaHub unter C:\\Program Files installiert ist, "
            f"muss der MediaHub-Ordner Schreibrechte besitzen."
        )
        raise