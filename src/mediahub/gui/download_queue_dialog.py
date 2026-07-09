from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton

from src.mediahub.gui.download_queue_panel import DownloadQueuePanel


class DownloadQueueDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Download-Warteschlange")
        self.resize(760, 480)
        self.setMinimumSize(640, 360)

        self.panel = DownloadQueuePanel(self)
        self.btn_close = QPushButton("Schließen")

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.panel, 1)
        layout.addLayout(button_layout)

        self.btn_close.clicked.connect(self.hide)

    @property
    def btn_cancel(self):
        return self.panel.btn_cancel

    def set_cancel_callback(self, callback):
        self.panel.set_cancel_callback(callback)

    def load_items(self, download_items):
        self.panel.load_items(download_items)

    def mark_running(self, index, title):
        self.panel.mark_running(index, title)

    def mark_done(self, index, title):
        self.panel.mark_done(index, title)

    def mark_failed(self, index, title):
        self.panel.mark_failed(index, title)

    def mark_cancelled(self, index, title):
        self.panel.mark_cancelled(index, title)

    def mark_members_only(self, index, title):
        self.panel.mark_members_only(index, title)

    def finish(self):
        self.panel.finish()

    def set_item_progress(self, value):
        self.panel.set_item_progress(value)

    def set_total_progress(self, value):
        self.panel.set_total_progress(value)
