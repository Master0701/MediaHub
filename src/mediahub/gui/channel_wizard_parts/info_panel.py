from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLabel,
    QWidget,
    QScrollArea,
)
from PySide6.QtCore import Qt

from src.mediahub.gui.channel_wizard_parts.avatar_widget import AvatarWidget


class ChannelWizardInfoPanel(QGroupBox):
    def __init__(self):
        super().__init__("Kanal-Informationen")

        outer_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)

        self.avatar_widget = AvatarWidget(size=120)

        self.name_label = QLabel("Noch kein Kanal geladen")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(
            "font-size:18px; font-weight:bold;"
        )

        self.url_label = QLabel("")
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.playlist_label = QLabel("Playlists: -")

        self.avatar_label = QLabel("Avatar: -")
        self.banner_label = QLabel("Banner: -")

        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.description_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(self.avatar_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        layout.addWidget(self.url_label)
        layout.addWidget(self.playlist_label)
        layout.addWidget(self.avatar_label)
        layout.addWidget(self.banner_label)
        layout.addWidget(self.description_label)
        layout.addStretch()

        scroll.setWidget(container)

        outer_layout.addWidget(scroll)

    def set_channel_info(
        self,
        name,
        url,
        description="",
        avatar="",
        banner="",
        playlist_count=0,
    ):
        self.name_label.setText(name or "Unbekannter Kanal")

        self.url_label.setText(
            f"<b>URL</b><br>{url or '-'}"
        )

        self.playlist_label.setText(
            f"<b>Playlists:</b> {playlist_count}"
        )

        avatar_loaded = self.avatar_widget.load_from_url(avatar)

        self.avatar_label.setText(
            "✅ Avatar geladen" if avatar_loaded else "❌ Avatar nicht gefunden"
        )

        self.banner_label.setText(
            "✅ Banner gefunden" if banner else "❌ Banner nicht gefunden"
        )

        if description:
            self.description_label.setText(
                "<b>Beschreibung</b><br><br>" + description.strip()
            )
        else:
            self.description_label.setText(
                "<b>Beschreibung</b><br><br>Keine Beschreibung vorhanden."
            )