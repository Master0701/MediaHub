from PySide6.QtWidgets import QPushButton, QLabel, QGroupBox

PANEL_MARGIN = 14
PANEL_SPACING = 10
BUTTON_HEIGHT = 36
SMALL_BUTTON_HEIGHT = 32
TITLE_STYLE = "font-size: 24px; font-weight: bold;"
SUBTITLE_STYLE = "color: #cfcfcf;"


def make_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(TITLE_STYLE)
    return label


def configure_button(button: QPushButton, tooltip: str | None = None, height: int = BUTTON_HEIGHT) -> QPushButton:
    button.setMinimumHeight(height)
    button.setMinimumWidth(130)
    if tooltip:
        button.setToolTip(tooltip)
    return button


def configure_group(group: QGroupBox) -> QGroupBox:
    group.setMinimumHeight(80)
    return group
