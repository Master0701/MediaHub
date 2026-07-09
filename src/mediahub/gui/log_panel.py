from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QGroupBox, QProgressBar, QLabel, QSizePolicy
from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor


class LogPanel(QWidget):
    def __init__(self):
        super().__init__()

        self._pending_messages = []
        self._pending_progress = None
        self._pending_status = None

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(250)
        self._flush_timer.timeout.connect(self._flush_pending_updates)

        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        box = QGroupBox("Log / Download")
        box.setMinimumHeight(0)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        box_layout = QVBoxLayout(box)

        self.status_label = QLabel("Bereit")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(0)
        self.log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.log.setText("MediaHub gestartet.\nv0.7.0-alpha aktiv.")

        box_layout.addWidget(self.status_label)
        box_layout.addWidget(self.progress)
        box_layout.addWidget(self.log)

        layout.addWidget(box)

    def write(self, message: str):
        # Wichtig: während yt-dlp läuft, kommen viele Meldungen kurz hintereinander.
        # Direkte QTextEdit-Updates konnten unter Windows Recursive-Repaint-Abstürze auslösen.
        self._pending_messages.append(str(message))
        self._ensure_flush_timer()

    def set_progress(self, value: int):
        try:
            self._pending_progress = max(0, min(100, int(value)))
        except Exception:
            self._pending_progress = 0
        self._ensure_flush_timer()

    def set_status(self, text: str):
        self._pending_status = str(text)
        self._ensure_flush_timer()

    def _ensure_flush_timer(self):
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def _flush_pending_updates(self):
        if self._pending_status is not None:
            if self.status_label.text() != self._pending_status:
                self.status_label.setText(self._pending_status)
            self._pending_status = None

        if self._pending_progress is not None:
            if self.progress.value() != self._pending_progress:
                self.progress.setValue(self._pending_progress)
            self._pending_progress = None

        if self._pending_messages:
            messages = self._pending_messages[:]
            self._pending_messages.clear()

            self.log.setUpdatesEnabled(False)
            cursor = self.log.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            text = "\n".join(messages)
            if self.log.toPlainText():
                text = "\n" + text
            cursor.insertText(text)
            self.log.setTextCursor(cursor)
            self.log.ensureCursorVisible()
            self.log.setUpdatesEnabled(True)

        if not self._pending_messages and self._pending_progress is None and self._pending_status is None:
            self._flush_timer.stop()
