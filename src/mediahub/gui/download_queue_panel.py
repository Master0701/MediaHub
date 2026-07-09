from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QProgressBar, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor


class DownloadQueuePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.items = []
        self._cancel_callback = None
        self._cancel_connected = False
        self._pending_actions = []
        self._pending_item_progress = None
        self._pending_total_progress = None

        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(300)
        self._ui_timer.timeout.connect(self._apply_pending_updates)

        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        self.title_label = QLabel("Download-Warteschlange")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.current_label = QLabel("Aktuell: -")
        self.count_label = QLabel("Gesamt: 0 / 0")

        self.queue_list = QListWidget()
        self.queue_list.setMinimumWidth(220)
        self.queue_list.setMinimumHeight(0)
        self.queue_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        self.item_progress = QProgressBar()
        self.item_progress.setRange(0, 100)
        self.item_progress.setValue(0)
        self.item_progress.setFormat("Aktuelles Video: %p%")

        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 100)
        self.total_progress.setValue(0)
        self.total_progress.setFormat("Gesamt: %p%")

        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.count_label)
        button_layout.addStretch(1)
        button_layout.addWidget(self.btn_cancel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.title_label)
        layout.addWidget(self.current_label)
        layout.addWidget(self.queue_list, 1)
        layout.addWidget(self.item_progress)
        layout.addWidget(self.total_progress)
        layout.addLayout(button_layout)

    def set_cancel_callback(self, callback):
        if self._cancel_connected:
            try:
                self.btn_cancel.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._cancel_connected = False

        self._cancel_callback = callback

        if callback is not None:
            self.btn_cancel.clicked.connect(callback)
            self._cancel_connected = True

    def load_items(self, download_items):
        self.items = list(download_items)
        self._pending_actions.clear()
        self._pending_item_progress = 0
        self._pending_total_progress = 0

        self.queue_list.setUpdatesEnabled(False)
        self.queue_list.clear()

        for item in self.items:
            title = item.get("title", "Ohne Titel")
            playlist = item.get("playlist", "")
            is_members = self._is_members_only_item(item)
            icon = "🔒" if is_members else "⏳"
            text = f"{icon} {title}"
            if playlist:
                text += f"  [{playlist}]"
            list_item = QListWidgetItem(text)
            if is_members:
                self._apply_members_style(list_item)
            self.queue_list.addItem(list_item)

        self.queue_list.setUpdatesEnabled(True)
        self.current_label.setText("Aktuell: -")
        self.update_count(0, len(self.items))
        self.item_progress.setValue(0)
        self.total_progress.setValue(0)
        self.btn_cancel.setEnabled(True)

    def mark_running(self, index, title):
        self._queue_action(("running", index, title))

    def mark_done(self, index, title):
        self._queue_action(("done", index, title))

    def mark_failed(self, index, title):
        self._queue_action(("failed", index, title))

    def mark_cancelled(self, index, title):
        self._queue_action(("cancelled", index, title))

    def mark_members_only(self, index, title):
        self._queue_action(("members_only", index, title))

    def finish(self):
        self._queue_action(("finish", 0, ""))

    def set_item_progress(self, value):
        self._pending_item_progress = self._clamp_progress(value)
        self._ensure_timer()

    def set_total_progress(self, value):
        self._pending_total_progress = self._clamp_progress(value)
        self._ensure_timer()

    def update_count(self, done, total):
        self.count_label.setText(f"Gesamt: {done} / {total}")

    def _queue_action(self, action):
        self._pending_actions.append(action)
        self._ensure_timer()

    def _ensure_timer(self):
        if not self._ui_timer.isActive():
            self._ui_timer.start()

    def _apply_pending_updates(self):
        actions = self._pending_actions[:]
        self._pending_actions.clear()

        if actions:
            self.queue_list.setUpdatesEnabled(False)
            for kind, index, title in actions:
                if kind == "running":
                    self._set_item_text(index, "▶", title)
                    self.current_label.setText(f"Aktuell: {title}")
                    self.update_count(index, len(self.items))
                    self.item_progress.setValue(0)
                elif kind == "done":
                    self._set_item_text(index, "✅", title)
                    self.update_count(index + 1, len(self.items))
                elif kind == "failed":
                    self._set_item_text(index, "❌", title)
                elif kind == "cancelled":
                    self._set_item_text(index, "⛔", title)
                    self.current_label.setText("Aktuell: abgebrochen")
                    self.btn_cancel.setEnabled(False)
                elif kind == "members_only":
                    self._set_item_text(index, "🔒", title, members_only=True)
                    self.current_label.setText("Aktuell: Mitglieder-Video übersprungen")
                elif kind == "finish":
                    self.current_label.setText("Aktuell: fertig")
                    self.update_count(len(self.items), len(self.items))
                    self.btn_cancel.setEnabled(False)
            self.queue_list.setUpdatesEnabled(True)

        if self._pending_item_progress is not None:
            if self.item_progress.value() != self._pending_item_progress:
                self.item_progress.setValue(self._pending_item_progress)
            self._pending_item_progress = None

        if self._pending_total_progress is not None:
            if self.total_progress.value() != self._pending_total_progress:
                self.total_progress.setValue(self._pending_total_progress)
            self._pending_total_progress = None

        if not self._pending_actions and self._pending_item_progress is None and self._pending_total_progress is None:
            self._ui_timer.stop()

    def _clamp_progress(self, value):
        try:
            return max(0, min(100, int(value)))
        except Exception:
            return 0

    def _set_item_text(self, index, icon, title, members_only=False):
        if index < 0 or index >= self.queue_list.count():
            return

        playlist = ""
        if index < len(self.items):
            playlist = self.items[index].get("playlist", "")

        text = f"{icon} {title}"
        if playlist:
            text += f"  [{playlist}]"

        item = self.queue_list.item(index)
        if item is not None:
            if item.text() != text:
                item.setText(text)
            if members_only or self._is_members_only_item(self.items[index] if index < len(self.items) else {}):
                self._apply_members_style(item)

    def _is_members_only_item(self, item):
        try:
            if int(item.get("is_members_only") or 0) == 1:
                return True
        except Exception:
            pass

        text = " ".join(str(item.get(key, "")) for key in ("title", "status", "error", "message")).lower()
        markers = (
            "members-only", "members only", "member-only",
            "channel's members", "channel members", "join this channel",
            "kanalmitglied", "kanalmitgliedschaft", "kanal-abonnenten",
            "zur kanal unterstützung", "zur kanal unterstuetzung",
        )
        return any(marker in text for marker in markers)

    def _apply_members_style(self, item):
        item.setBackground(QColor(150, 30, 30))
        item.setForeground(QColor(255, 245, 245))
        item.setToolTip("Dieses Video ist nur für Kanalmitglieder/Abonnenten verfügbar.")
