from time import monotonic

from PySide6.QtCore import QObject, Signal, Slot


class DownloadWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    queue_progress = Signal(int)
    current_item = Signal(str)
    item_started = Signal(int, str)
    item_finished = Signal(int, str)
    item_cancelled = Signal(int, str)
    item_members_only = Signal(int, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, download_service, download_items):
        super().__init__()
        self.download_service = download_service
        self.download_items = download_items
        self.is_cancelled = False
        self._last_progress_emit = 0.0
        self._last_log_emit = 0.0
        self._last_progress_value = -1

    @Slot()
    def cancel(self):
        self.is_cancelled = True

    def _safe_progress(self, value):
        try:
            value = max(0, min(100, int(value)))
        except Exception:
            value = 0

        now = monotonic()
        # yt-dlp kann extrem viele Fortschrittsmeldungen pro Sekunde senden.
        # Zu viele GUI-Signale konnten das Fenster beim Download instabil machen.
        if value in (0, 100) or value != self._last_progress_value and now - self._last_progress_emit >= 0.25:
            self._last_progress_value = value
            self._last_progress_emit = now
            self.progress.emit(value)

    def _safe_log(self, message):
        message = str(message)
        now = monotonic()

        # Laufende Download-Zeilen werden gedrosselt, wichtige Meldungen bleiben direkt sichtbar.
        if message.startswith("Download läuft:"):
            if now - self._last_log_emit < 1.0:
                return
            self._last_log_emit = now

        self.log.emit(message)

    @Slot()
    def run(self):
        try:
            total = len(self.download_items)

            if total == 0:
                self.log.emit("Keine Downloads in der Warteschlange.")
                self.finished.emit()
                return

            self.queue_progress.emit(0)

            for index, item in enumerate(self.download_items, start=1):
                if self.is_cancelled:
                    self.log.emit("Warteschlange wurde abgebrochen.")
                    self.finished.emit()
                    return

                channel = item["channel"]
                title = item.get("title", "Ohne Titel")

                item_index = index - 1
                self.current_item.emit(title)
                self.item_started.emit(item_index, title)
                self.log.emit(f"Starte Download {index}/{total}: {title}")
                self.queue_progress.emit(int(((index - 1) / total) * 100))
                self._safe_progress(0)

                success = self.download_service.download_latest_video(
                    channel,
                    log_callback=self._safe_log,
                    progress_callback=self._safe_progress,
                    cancel_callback=lambda: self.is_cancelled,
                )

                if self.is_cancelled:
                    self.log.emit("Warteschlange wurde abgebrochen.")
                    self.item_cancelled.emit(item_index, title)
                    self.current_item.emit("")
                    self.finished.emit()
                    return

                status = success
                if status is False and getattr(self.download_service, "last_download_status", "") == "members_only":
                    status = "members_only"

                if status == "members_only":
                    video_id = item.get("video_id", "") or getattr(channel, "video_id", "")
                    repository = item.get("repository") or getattr(self.download_service, "repository", None)
                    if repository is not None and video_id:
                        try:
                            repository.mark_video_members_only(
                                video_id,
                                "Download meldete Mitglieder-Video",
                                title=title,
                                url=getattr(channel, "url", ""),
                                channel_name=getattr(channel, "name", ""),
                            )
                            self.log.emit(f"🔒 In Datenbank als Mitglieder-Video markiert: {video_id}")
                        except Exception as error:
                            self.log.emit(f"Mitgliederstatus konnte nicht gespeichert werden: {error}")
                    elif not video_id:
                        self.log.emit("Mitgliederstatus konnte nicht gespeichert werden: Video-ID fehlt.")
                    else:
                        self.log.emit("Mitgliederstatus konnte nicht gespeichert werden: Repository fehlt.")

                    self.log.emit(f"🔒 Mitglieder-Video übersprungen: {title}")
                    self.item_members_only.emit(item_index, title)
                    self.queue_progress.emit(int((index / total) * 100))
                    continue

                if success is False:
                    self.log.emit(f"Download/Import fehlgeschlagen, überspringe: {title}")
                    self.item_cancelled.emit(item_index, title)
                    self.queue_progress.emit(int((index / total) * 100))
                    continue

                video_id = item.get("video_id", "") or getattr(channel, "video_id", "")
                repository = item.get("repository") or getattr(self.download_service, "repository", None)
                downloaded_files = list(
                    getattr(self.download_service, "last_downloaded_files", []) or []
                )
                downloaded_file = downloaded_files[0] if downloaded_files else ""

                if repository is not None and video_id and downloaded_file:
                    try:
                        path = __import__("pathlib").Path(downloaded_file)
                        repository.mark_video_downloaded(
                            video_id=video_id,
                            filename=str(path),
                            has_nfo=path.with_suffix(".nfo").exists(),
                            has_thumbnail=any(
                                path.with_suffix(ext).exists()
                                for ext in (".jpg", ".jpeg", ".png", ".webp")
                            ),
                            title=title,
                            url=getattr(channel, "url", ""),
                            channel_name=getattr(channel, "name", ""),
                        )
                        self.log.emit(f"✅ In Datenbank als geladen gespeichert: {path}")
                    except Exception as error:
                        self.log.emit(f"Downloadstatus konnte nicht gespeichert werden: {error}")
                elif not video_id:
                    self.log.emit("Downloadstatus konnte nicht gespeichert werden: Video-ID fehlt.")
                elif repository is None:
                    self.log.emit("Downloadstatus konnte nicht gespeichert werden: Repository fehlt.")
                else:
                    self.log.emit("Downloadstatus konnte nicht gespeichert werden: Dateipfad fehlt.")

                self._safe_progress(100)
                self.item_finished.emit(item_index, title)
                self.queue_progress.emit(int((index / total) * 100))

            self.current_item.emit("")
            self.queue_progress.emit(100)
            self.finished.emit()

        except Exception as error:
            self.error.emit(f"{type(error).__name__}: {error}")
