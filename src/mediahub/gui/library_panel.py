from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer, QObject, QThread, Signal, Slot
from PySide6.QtGui import QDesktopServices, QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QGroupBox, QFormLayout, QSplitter, QMenu, QMessageBox
)


class LibrarySearchWorker(QObject):
    finished = Signal(int, list, str)

    def __init__(self, request_id, repository, query, status_filter, limit):
        super().__init__()
        self.request_id = request_id
        self.repository = repository
        self.query = query
        self.status_filter = status_filter
        self.limit = limit

    @Slot()
    def run(self):
        try:
            rows = self.repository.search_library_videos(
                query=self.query,
                status_filter=self.status_filter,
                limit=self.limit,
            )
            self.finished.emit(self.request_id, rows, "")
        except Exception as error:
            self.finished.emit(self.request_id, [], str(error))


class LibraryPanel(QWidget):
    """Bibliotheksansicht für bekannte Videos aus SQLite."""

    def __init__(self, repository=None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.current_rows = []
        self._refresh_pending = False
        self._loaded_once = False
        self._search_request_id = 0
        self._search_thread = None
        self._search_worker = None

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._run_scheduled_refresh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        self.title = QLabel("📚 Bibliothek")
        self.title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.counter = QLabel("0 Videos")
        self.counter.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(self.title)
        title_row.addStretch()
        title_row.addWidget(self.counter)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Suche:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Titel, Kanal, Playlist oder Video-ID suchen ...")
        self.search_input.textChanged.connect(self._on_search_text_changed)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Alle Videos", "all")
        self.filter_combo.addItem("Nur neue", "new")
        self.filter_combo.addItem("Nur geladen", "downloaded")
        self.filter_combo.addItem("Nur Mitglieder", "members")
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(lambda: self.schedule_refresh(delay=0))

        filter_row.addWidget(self.search_input, 1)
        filter_row.addWidget(self.filter_combo)
        filter_row.addWidget(self.btn_refresh)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Titel", "Kanal", "Playlist", "Status", "Upload", "Video-ID"
        ])
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.itemSelectionChanged.connect(self.update_details_from_selection)
        self.table.itemDoubleClicked.connect(lambda _item: self.open_selected_video())
        self.table.customContextMenuRequested.connect(self.open_context_menu)

        self.detail_box = QGroupBox("Details")
        detail_layout = QVBoxLayout(self.detail_box)
        detail_layout.setContentsMargins(8, 8, 8, 8)
        detail_layout.setSpacing(6)

        detail_form = QFormLayout()
        detail_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.detail_title = QLabel("-")
        self.detail_title.setWordWrap(True)
        self.detail_channel = QLabel("-")
        self.detail_playlist = QLabel("-")
        self.detail_status = QLabel("-")
        self.detail_upload = QLabel("-")
        self.detail_duration = QLabel("-")
        self.detail_video_id = QLabel("-")
        self.detail_url = QLabel("-")
        self.detail_url.setWordWrap(True)
        self.detail_file = QLabel("-")
        self.detail_file.setWordWrap(True)
        self.detail_sync = QLabel("-")

        detail_form.addRow("Titel:", self.detail_title)
        detail_form.addRow("Kanal:", self.detail_channel)
        detail_form.addRow("Playlist:", self.detail_playlist)
        detail_form.addRow("Status:", self.detail_status)
        detail_form.addRow("Upload:", self.detail_upload)
        detail_form.addRow("Dauer:", self.detail_duration)
        detail_form.addRow("Video-ID:", self.detail_video_id)
        detail_form.addRow("URL:", self.detail_url)
        detail_form.addRow("Datei:", self.detail_file)
        detail_form.addRow("Letzte Sync:", self.detail_sync)

        self.detail_description = QTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setPlaceholderText("Keine Beschreibung gespeichert.")
        self.detail_description.setMinimumHeight(70)

        detail_layout.addLayout(detail_form)
        detail_layout.addWidget(QLabel("Beschreibung:"))
        detail_layout.addWidget(self.detail_description, 1)

        content_splitter = QSplitter(Qt.Orientation.Vertical)
        content_splitter.setHandleWidth(8)
        content_splitter.addWidget(self.table)
        content_splitter.addWidget(self.detail_box)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([320, 160])

        self.loading_label = QLabel("Bereit")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.loading_label.setStyleSheet("color: #9aa4ad;")

        footer_row = QHBoxLayout()
        footer_row.addStretch()
        footer_row.addWidget(self.loading_label)

        layout.addLayout(title_row)
        layout.addLayout(filter_row)
        layout.addWidget(content_splitter, 1)
        layout.addLayout(footer_row)

        self.show_loading_message("Bibliothek wird beim ersten Öffnen geladen ...")

    def set_repository(self, repository):
        self.repository = repository
        self.schedule_refresh(delay=150)

    def show_loading_message(self, text="Lade Bibliothek ..."):
        self.loading_label.setText(text)

    def _on_search_text_changed(self, _text):
        self.schedule_refresh(delay=450)

    def _on_filter_changed(self, _index):
        self.schedule_refresh(delay=250)

    def schedule_refresh(self, delay=450):
        self._refresh_pending = True
        query = self.search_input.text().strip()
        if query:
            self.show_loading_message("Suche läuft gleich ...")
        else:
            self.show_loading_message("Lade Bibliothek ...")

        try:
            delay_ms = int(delay)
        except (TypeError, ValueError):
            delay_ms = 450

        self.search_timer.start(max(0, delay_ms))

    def _run_scheduled_refresh(self):
        self._refresh_pending = False
        self.refresh()

    def refresh(self):
        if self.repository is None:
            self.table.setRowCount(0)
            self.counter.setText("Keine Datenbank")
            return

        query = self.search_input.text().strip()
        status_filter = self.filter_combo.currentData() or "all"
        limit = 250 if not query and status_filter == "all" else 300

        # Alte Suchergebnisse werden ignoriert, wenn inzwischen eine neue Suche gestartet wurde.
        self._search_request_id += 1
        request_id = self._search_request_id

        self.btn_refresh.setEnabled(False)
        self.show_loading_message("Suche läuft ...")

        thread = QThread(self)
        worker = LibrarySearchWorker(request_id, self.repository, query, status_filter, limit)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_search_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._clear_search_thread(thread))

        self._search_thread = thread
        self._search_worker = worker
        thread.start()

    def _clear_search_thread(self, thread):
        if self._search_thread is thread:
            self._search_thread = None
            self._search_worker = None

    def _handle_search_finished(self, request_id, rows, error_message):
        if request_id != self._search_request_id:
            return

        self.btn_refresh.setEnabled(True)

        if error_message:
            self.current_rows = []
            self.table.setRowCount(1)
            self.counter.setText("Fehler")
            self.loading_label.setText("Fehler beim Laden")
            item = QTableWidgetItem(f"Bibliothek konnte nicht geladen werden: {error_message}")
            self.table.setItem(0, 0, item)
            self.clear_details()
            return

        self.current_rows = rows
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            is_members = self._is_members_only_row(row)
            title_text = str(row.get("title", "") or "")
            if is_members and not title_text.startswith("🔒"):
                title_text = f"🔒 {title_text}"

            values = [
                title_text,
                row.get("channel_name", ""),
                row.get("playlists", ""),
                self._status_text(row),
                row.get("upload_date", ""),
                row.get("video_id", ""),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                if column in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if is_members:
                    self._apply_members_style(item)
                self.table.setItem(row_index, column, item)

        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(False)

        query = self.search_input.text().strip()
        status_filter = self.filter_combo.currentData() or "all"
        max_limit = 250 if not query and status_filter == "all" else 300
        suffix = "" if len(rows) < max_limit else f" (max. {max_limit} angezeigt)"
        members_count = sum(1 for row in rows if self._is_members_only_row(row))
        if members_count:
            self.counter.setText(f"{len(rows)} Videos | 🔴 🔒 {members_count} Mitglieder{suffix}")
        else:
            self.counter.setText(f"{len(rows)} Videos{suffix}")
        self.loading_label.setText("Bibliothek geladen")
        self._loaded_once = True
        if rows:
            self.table.selectRow(0)
        else:
            self.clear_details()

    def update_details_from_selection(self):
        row = self.selected_row()
        if row is None:
            self.clear_details()
            return

        self.detail_title.setText(str(row.get("title") or "-"))
        self.detail_channel.setText(str(row.get("channel_name") or "-"))
        self.detail_playlist.setText(str(row.get("playlists") or "-"))
        self.detail_status.setText(self._status_text(row))
        self.detail_upload.setText(str(row.get("upload_date") or "-"))
        self.detail_duration.setText(self._duration_text(row.get("duration")))
        self.detail_video_id.setText(str(row.get("video_id") or "-"))
        self.detail_url.setText(str(row.get("url") or "-"))
        self.detail_file.setText(str(row.get("downloaded_filename") or "-"))
        self.detail_sync.setText(str(row.get("last_sync_at") or row.get("last_seen_at") or "-"))
        self.detail_description.setPlainText(str(row.get("description") or ""))

    def selected_row(self):
        selection_model = self.table.selectionModel()
        selected = selection_model.selectedRows() if selection_model else []
        if not selected:
            return None

        row_index = selected[0].row()
        if row_index < 0 or row_index >= len(self.current_rows):
            return None
        return self.current_rows[row_index]

    def open_context_menu(self, position):
        row_index = self.table.indexAt(position).row()
        if row_index >= 0:
            self.table.selectRow(row_index)

        row = self.selected_row()
        if row is None:
            return

        has_file = self._local_file_path(row) is not None
        has_url = bool(row.get("url") or row.get("video_id"))

        menu = QMenu(self)
        action_open_video = menu.addAction("▶ Video öffnen")
        action_open_folder = menu.addAction("📂 Ordner öffnen")
        menu.addSeparator()
        action_open_youtube = menu.addAction("🌐 Auf YouTube öffnen")
        action_copy_url = menu.addAction("🔗 YouTube-Link kopieren")
        menu.addSeparator()
        action_refresh = menu.addAction("🔄 Bibliothek aktualisieren")

        action_open_video.setEnabled(has_file or has_url)
        action_open_folder.setEnabled(has_file)
        action_open_youtube.setEnabled(has_url)
        action_copy_url.setEnabled(has_url)

        chosen = menu.exec(self.table.viewport().mapToGlobal(position))
        if chosen == action_open_video:
            self.open_selected_video()
        elif chosen == action_open_folder:
            self.open_selected_folder()
        elif chosen == action_open_youtube:
            self.open_selected_youtube()
        elif chosen == action_copy_url:
            self.copy_selected_url()
        elif chosen == action_refresh:
            self.schedule_refresh(delay=0)

    def open_selected_video(self):
        row = self.selected_row()
        if row is None:
            return

        file_path = self._local_file_path(row)
        if file_path is not None:
            self._open_local_path(file_path)
            return

        self.open_selected_youtube()

    def open_selected_folder(self):
        row = self.selected_row()
        if row is None:
            return

        file_path = self._local_file_path(row)
        if file_path is None:
            QMessageBox.information(self, "Bibliothek", "Zu diesem Video ist keine lokale Datei gespeichert.")
            return

        self._open_local_path(file_path.parent)

    def open_selected_youtube(self):
        row = self.selected_row()
        if row is None:
            return

        url = self._youtube_url(row)
        if not url:
            QMessageBox.information(self, "Bibliothek", "Zu diesem Video ist keine YouTube-URL gespeichert.")
            return

        QDesktopServices.openUrl(QUrl(url))

    def copy_selected_url(self):
        row = self.selected_row()
        if row is None:
            return

        url = self._youtube_url(row)
        if not url:
            return

        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(url)

    def clear_details(self):
        for label in (
            self.detail_title, self.detail_channel, self.detail_playlist,
            self.detail_status, self.detail_upload, self.detail_duration,
            self.detail_video_id, self.detail_url, self.detail_file, self.detail_sync,
        ):
            label.setText("-")
        self.detail_description.clear()


    def _apply_members_style(self, item: QTableWidgetItem):
        # Extra robust: Qt-Stylesheets/Themes können setBackground() überdecken.
        # Deshalb setzen wir BackgroundRole/ForegroundRole UND den normalen Brush.
        background = QBrush(QColor(170, 25, 25))
        foreground = QBrush(QColor(255, 255, 255))
        item.setBackground(background)
        item.setForeground(foreground)
        item.setData(Qt.ItemDataRole.BackgroundRole, background)
        item.setData(Qt.ItemDataRole.ForegroundRole, foreground)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setToolTip("🔒 Dieses Video ist nur für Kanalmitglieder/Abonnenten verfügbar.")

    def _is_members_only_row(self, row: dict) -> bool:
        if int(row.get("is_members_only") or 0) == 1:
            return True

        text = " ".join(
            str(row.get(key, ""))
            for key in ("title", "status", "availability", "error", "message")
        ).lower()
        markers = (
            "members-only", "members only", "member-only",
            "channel's members", "channel members", "join this channel",
            "kanalmitglied", "kanalmitgliedschaft", "kanal-abonnenten",
            "abo-video", "subscriber-only", "subscribers only",
            "premium_only", "premium only", "requires payment",
            "zur kanal unterstützung", "zur kanal unterstuetzung",
        )
        return any(marker in text for marker in markers)

    def _duration_text(self, value) -> str:
        try:
            seconds = int(value or 0)
        except (TypeError, ValueError):
            seconds = 0
        if seconds <= 0:
            return "-"
        hours, rest = divmod(seconds, 3600)
        minutes, seconds = divmod(rest, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def _status_text(self, row: dict) -> str:
        status = str(row.get("status") or "").lower()
        if self._is_members_only_row(row) or status in {"members_only", "member", "members"}:
            return "🔴 🔒 Mitglieder"
        if status in {"error", "failed"}:
            return "🔴 Fehler"
        if int(row.get("is_downloaded") or 0) == 1:
            return "🟢 Geladen"
        if int(row.get("is_new") or 0) == 1:
            return "🟡 Neu"
        return "⚪ Bekannt"

    def _youtube_url(self, row: dict) -> str:
        url = str(row.get("url") or "").strip()
        if url:
            return url

        video_id = str(row.get("video_id") or "").strip()
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        return ""

    def _local_file_path(self, row: dict):
        filename = str(row.get("downloaded_filename") or "").strip()
        if not filename:
            return None

        path = Path(filename)
        if not path.is_absolute():
            path = Path.cwd() / path

        if path.exists():
            return path
        return None

    def _open_local_path(self, path: Path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
