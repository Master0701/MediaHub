from urllib.request import urlopen

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class AvatarWidget(QLabel):
    def __init__(self, size=120):
        super().__init__()

        self.size = size

        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Kein\nAvatar")
        self.setStyleSheet(
            "border: 1px solid #555;"
            "border-radius: 8px;"
            "background-color: #222;"
            "color: #aaa;"
        )

    def clear_avatar(self):
        self.setPixmap(QPixmap())
        self.setText("Kein\nAvatar")

    def load_from_url(self, url):
        if not url:
            self.clear_avatar()
            return False

        try:
            with urlopen(url, timeout=10) as response:
                data = response.read()

            pixmap = QPixmap()
            pixmap.loadFromData(data)

            if pixmap.isNull():
                self.clear_avatar()
                return False

            scaled = pixmap.scaled(
                self.size,
                self.size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.setText("")
            self.setPixmap(scaled)
            return True

        except Exception:
            self.clear_avatar()
            return False