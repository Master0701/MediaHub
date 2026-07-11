from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None

from PySide6.QtCore import QObject, QThread, Slot
from PySide6.QtWidgets import QMessageBox

from src.mediahub.gui.download_worker import DownloadWorker
from src.mediahub.gui.download_queue_dialog import DownloadQueueDialog


class DownloadUiBridge(QObject):
    """Leitet Worker-Signale sicher in den GUI-Thread weiter.

    DownloadWorker läuft in einem eigenen QThread. Direkte Aufrufe auf
    DownloadQueuePanel konnten QTimer aus dem Worker-Thread starten und
    dadurch Abstürze/Repaint-Fehler auslösen. Dieses QObject lebt im
    Hauptfenster-Thread; seine Slots werden deshalb per Qt sicher im
    GUI-Thread ausgeführt.
    """

    def __init__(self, manager):
        super().__init__(manager.main_window)
        self.manager = manager

    @Slot(int)
    def item_progress(self, value):
        self.manager.on_item_progress(value)

    @Slot(int)
    def queue_progress(self, value):
        self.manager.on_queue_progress(value)

    @Slot(str)
    def current_item(self, title):
        self.manager.on_current_download_item(title)

    @Slot(int, str)
    def item_started(self, index, title):
        self.manager.on_item_started(index, title)

    @Slot(int, str)
    def item_finished(self, index, title):
        self.manager.on_item_finished(index, title)

    @Slot(int, str)
    def item_cancelled(self, index, title):
        self.manager.on_item_cancelled(index, title)

    @Slot(int, str)
    def item_members_only(self, index, title):
        self.manager.on_item_members_only(index, title)

    @Slot()
    def download_finished(self):
        self.manager.on_download_finished()

    @Slot(str)
    def download_error(self, error):
        self.manager.on_download_error(error)


class DownloadManager:
    def __init__(
        self,
        main_window,
        download_service,
        tool_service,
        log_panel,
        update_status_callback,
        queue_panel=None,
    ):
        self.main_window = main_window
        self.download_service = download_service
        self.tool_service = tool_service
        self.log_panel = log_panel
        self.update_status = update_status_callback

        self.download_thread = None
        self.download_worker = None
        self.queue_panel = queue_panel
        self.queue_dialog = None
        self.ui_bridge = DownloadUiBridge(self)
        self._public_download_status = {
            "active": False,
            "status": "Kein Download aktiv",
            "current_title": "",
            "item_progress": 0,
            "total_progress": 0,
            "done_count": 0,
            "total_count": 0,
            "queue": [],
        }

        if self.queue_panel is not None:
            self.queue_panel.set_cancel_callback(self.cancel_download)

    def can_start_download(self):
        missing = self.tool_service.missing_tools()

        if missing:
            self.log_panel.write("Download abgebrochen: Tools fehlen.")
            self.update_status("Tools fehlen")
            return False

        if self.download_thread is not None:
            self.log_panel.write("Es läuft bereits ein Download.")
            return False

        return True

    def start_download_queue(self, channel, videos):
        if not self.can_start_download():
            return

        videos = self._confirm_members_only_videos(list(videos or []))
        if not videos:
            self.log_panel.write("Keine Videos für den Download ausgewählt.")
            self.update_status("Kein Download gestartet")
            return

        download_items = self.build_download_items(channel, videos)

        self._load_queue_items(download_items)
        self._auto_open_queue_dialog()

        self.update_status("Download-Warteschlange läuft")
        self.log_panel.set_status(f"Warteschlange: {len(download_items)} Videos")
        self.log_panel.set_progress(0)
        self.log_panel.write(f"{len(download_items)} Videos in Warteschlange.")

        self.download_thread = QThread(self.main_window)
        self.download_worker = DownloadWorker(self.download_service, download_items)

        self.download_worker.moveToThread(self.download_thread)

        self.download_thread.started.connect(self.download_worker.run)

        self.download_worker.log.connect(self.log_panel.write)
        self.download_worker.progress.connect(self.log_panel.set_progress)
        self.download_worker.progress.connect(self.ui_bridge.item_progress)
        self.download_worker.queue_progress.connect(self.ui_bridge.queue_progress)
        self.download_worker.current_item.connect(self.ui_bridge.current_item)
        self.download_worker.item_started.connect(self.ui_bridge.item_started)
        self.download_worker.item_finished.connect(self.ui_bridge.item_finished)
        self.download_worker.item_cancelled.connect(self.ui_bridge.item_cancelled)
        if hasattr(self.download_worker, "item_members_only"):
            self.download_worker.item_members_only.connect(self.ui_bridge.item_members_only)

        self.download_worker.finished.connect(self.ui_bridge.download_finished)
        self.download_worker.error.connect(self.ui_bridge.download_error)

        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.error.connect(self.download_thread.quit)

        self.download_worker.finished.connect(self.download_worker.deleteLater)
        self.download_worker.error.connect(self.download_worker.deleteLater)

        self.download_thread.finished.connect(self.cleanup_download_thread)

        self.download_thread.start()

    def open_queue_dialog(self, download_items=None):
        if download_items is not None:
            self._load_queue_items(download_items)

        self._show_queue_dialog(focus=True)

    def _auto_open_queue_dialog(self):
        """Öffnet die Warteschlange automatisch beim Downloadstart.

        Das Fenster wird nur erstellt/angezeigt, wenn ein Download wirklich
        startet. Falls es schon offen ist, wird es nur nach vorne geholt.
        """
        self._show_queue_dialog(focus=True)

    def _show_queue_dialog(self, focus=False):
        if self.queue_dialog is None:
            self.queue_dialog = DownloadQueueDialog(self.main_window)
            self.queue_dialog.set_cancel_callback(self.cancel_download)

        if self.queue_panel is not None and self.queue_panel.items:
            self.queue_dialog.load_items(self.queue_panel.items)

        self.queue_dialog.show()

        if focus:
            self.queue_dialog.raise_()
            self.queue_dialog.activateWindow()

    def get_public_download_status(self):
        snapshot = dict(self._public_download_status)
        snapshot["queue"] = [dict(item) for item in self._public_download_status.get("queue", [])]
        return snapshot

    def _set_public_item_status(self, index, status, progress=None):
        queue = self._public_download_status.get("queue", [])
        if 0 <= index < len(queue):
            queue[index]["status"] = status
            if progress is not None:
                queue[index]["progress"] = max(0, min(100, int(progress)))

    def _load_queue_items(self, download_items):
        public_queue = []
        for item in list(download_items or []):
            public_queue.append({
                "title": str(item.get("title", "Ohne Titel")),
                "playlist": str(item.get("playlist", "")),
                "status": "members_only" if int(item.get("is_members_only") or 0) == 1 else "waiting",
                "progress": 0,
            })
        self._public_download_status.update({
            "active": bool(public_queue),
            "status": "Warteschlange vorbereitet" if public_queue else "Kein Download aktiv",
            "current_title": "",
            "item_progress": 0,
            "total_progress": 0,
            "done_count": 0,
            "total_count": len(public_queue),
            "queue": public_queue,
        })
        if self.queue_panel is not None:
            self.queue_panel.load_items(download_items)

        if self.queue_dialog is not None:
            self.queue_dialog.load_items(download_items)

    def _queue_views(self):
        views = []
        if self.queue_panel is not None:
            views.append(self.queue_panel)
        if self.queue_dialog is not None:
            views.append(self.queue_dialog)
        return views

    def cancel_download(self):
        if self.download_worker is None:
            self.log_panel.write("Kein laufender Download zum Abbrechen.")
            self.update_status("Kein Download aktiv")
            return

        self.download_worker.cancel()
        self.log_panel.write("Abbruch angefordert. Der aktuelle Download stoppt gleich.")
        self.log_panel.set_status("Download wird abgebrochen...")
        self.update_status("Download wird abgebrochen")


    def _is_members_only_video(self, video):
        if int(video.get("is_members_only") or 0) == 1:
            return True

        text = " ".join(
            str(video.get(key, ""))
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

    def _confirm_members_only_videos(self, videos):
        members = [video for video in videos if self._is_members_only_video(video)]
        if not members:
            return videos

        preview_titles = "\n".join(
            f"• {video.get('title', 'Ohne Titel')}"
            for video in members[:8]
        )
        if len(members) > 8:
            preview_titles += f"\n… und {len(members) - 8} weitere"

        message = (
            "Die Auswahl enthält Mitglieder-/Abo-Videos.\n\n"
            "Diese Downloads werden wahrscheinlich fehlschlagen.\n\n"
            f"{preview_titles}\n\n"
            "Trotzdem versuchen?"
        )

        answer = QMessageBox.question(
            self.main_window,
            "Mitglieder-Videos",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer == QMessageBox.StandardButton.Yes:
            return videos

        kept = [video for video in videos if not self._is_members_only_video(video)]
        skipped = len(videos) - len(kept)
        if skipped:
            self.log_panel.write(f"🔒 {skipped} Mitglieder-/Abo-Videos übersprungen.")
        return kept

    def _image_signature(self, path: Path, size: tuple[int, int] = (16, 16)):
        if Image is None:
            return None

        try:
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail(size, Image.LANCZOS)
                canvas = Image.new("RGB", size, (0, 0, 0))
                x = (size[0] - image.width) // 2
                y = (size[1] - image.height) // 2
                canvas.paste(image, (x, y))
                pixels = list(canvas.getdata())
                return tuple((r // 16, g // 16, b // 16) for r, g, b in pixels)
        except Exception:
            return None

    def _images_look_same(self, a: Path, b: Path, tolerance: int = 24) -> bool:
        try:
            a = Path(a)
            b = Path(b)

            if not a.exists() or not b.exists():
                return False

            if a.resolve() == b.resolve():
                return True

            if a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes():
                return True

            sig_a = self._image_signature(a)
            sig_b = self._image_signature(b)

            if sig_a is None or sig_b is None or len(sig_a) != len(sig_b):
                return False

            diff = 0
            for pa, pb in zip(sig_a, sig_b):
                diff += abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])

            return diff <= tolerance
        except Exception:
            return False


    def _clean_playlist_image(self, channel, value: str) -> str:
        """Akzeptiert nur echte lokale Playlistbilder.

        Ein Staffelposter darf nicht versehentlich Kanalposter/Fanart sein.
        Zusätzlich wird auch visuell geprüft, ob die Datei wie das Kanalbild aussieht.
        """
        text = str(value or "").strip()
        if not text:
            return ""

        try:
            path = Path(text)
            if not path.exists() or not path.is_file():
                return ""

            resolved = path.resolve()

            for other in (
                str(getattr(channel, "poster", "") or "").strip(),
                str(getattr(channel, "fanart", "") or "").strip(),
            ):
                if not other:
                    continue

                other_path = Path(other)
                if not other_path.exists():
                    continue

                if other_path.resolve() == resolved:
                    return ""

                if self._images_look_same(path, other_path):
                    try:
                        self.log_panel.write("Playlistbild verworfen: sieht wie Kanalbild/Banner aus.")
                    except Exception:
                        pass
                    return ""

            return str(path)
        except Exception:
            return ""


    def _playlist_image_for_video(self, channel, video: dict) -> str:
        playlist_id = str(video.get("playlist_id") or "").strip()
        playlist_name = str(video.get("playlist") or video.get("playlist_original") or "").strip()

        for setting in getattr(channel, "playlist_settings", []) or []:
            setting_id = str(setting.get("playlist_id") or "").strip()
            setting_name = str(setting.get("display_name") or setting.get("playlist_name") or "").strip()
            original_name = str(setting.get("playlist_name") or "").strip()

            if playlist_id and setting_id and playlist_id == setting_id:
                return self._clean_playlist_image(channel, str(setting.get("image_path") or ""))

            if playlist_name and playlist_name in {setting_name, original_name}:
                return self._clean_playlist_image(channel, str(setting.get("image_path") or ""))

        return ""

    def build_download_items(self, channel, videos):
        download_items = []

        for video in videos:
            video_url = video.get("url") or channel.url
            playlist_name = video.get("playlist", "")
            playlist_original = video.get("playlist_original", "")
            playlist_id = video.get("playlist_id", "")
            playlist_season = int(video.get("playlist_season", 1))
            playlist_folder_mode = getattr(channel, "playlist_folder_mode", "Nur Staffeln")
            playlist_image = self._playlist_image_for_video(channel, video)

            download_channel = type("DownloadChannel", (), {})()
            download_channel.__dict__.update(channel.__dict__)

            # Für den Download muss url die Video-URL sein.
            # Für tvshow.nfo behalten wir zusätzlich die echte Kanal-URL.
            download_channel.channel_url = getattr(channel, "url", "")
            download_channel.original_channel_url = getattr(channel, "url", "")
            download_channel.url = video_url

            download_channel.playlist_name = playlist_name
            download_channel.playlist_original = playlist_original
            download_channel.playlist_id = playlist_id
            download_channel.playlist_season = playlist_season
            download_channel.playlist_folder_mode = playlist_folder_mode
            download_channel.playlist_image = playlist_image

            video_id = video.get("video_id") or video.get("id") or ""
            download_channel.video_id = video_id

            repository = getattr(self.main_window, "repository", None)
            if repository is None:
                repository = getattr(getattr(self.main_window, "controller", None), "repository", None)
            if repository is None and hasattr(self.main_window, "library_panel"):
                repository = getattr(self.main_window.library_panel, "repository", None)
            if repository is None and hasattr(self.main_window, "repository_service"):
                repository = getattr(self.main_window, "repository_service", None)

            download_items.append({
                "channel": download_channel,
                "title": video.get("title", "Ohne Titel"),
                "playlist": playlist_name,
                "playlist_original": playlist_original,
                "playlist_id": playlist_id,
                "playlist_season": playlist_season,
                "playlist_folder_mode": playlist_folder_mode,
                "playlist_image": playlist_image,
                "video_id": video_id,
                "is_members_only": 1 if self._is_members_only_video(video) else 0,
                "repository": repository,
            })

        return download_items

    def on_item_progress(self, value):
        value = max(0, min(100, int(value)))
        self._public_download_status["item_progress"] = value
        queue = self._public_download_status.get("queue", [])
        for index, item in enumerate(queue):
            if item.get("status") == "running":
                self._set_public_item_status(index, "running", value)
                break
        for view in self._queue_views():
            view.set_item_progress(value)

    def on_queue_progress(self, value):
        self._public_download_status["total_progress"] = max(0, min(100, int(value)))
        # Statusbar nicht bei jedem Fortschritt neu zeichnen; das vermeidet Repaint-Stress.
        for view in self._queue_views():
            view.set_total_progress(value)

    def on_item_started(self, index, title):
        self._public_download_status.update({"active": True, "status": "Download läuft", "current_title": str(title), "item_progress": 0})
        self._set_public_item_status(index, "running", 0)
        for view in self._queue_views():
            view.mark_running(index, title)

    def on_item_finished(self, index, title):
        self._set_public_item_status(index, "done", 100)
        self._public_download_status["done_count"] = max(self._public_download_status.get("done_count", 0), index + 1)
        self._public_download_status["item_progress"] = 100
        for view in self._queue_views():
            view.mark_done(index, title)

    def on_item_cancelled(self, index, title):
        self._set_public_item_status(index, "cancelled")
        self._public_download_status.update({"active": False, "status": "Download abgebrochen", "current_title": str(title)})
        for view in self._queue_views():
            view.mark_cancelled(index, title)


    def on_item_members_only(self, index, title):
        self._set_public_item_status(index, "members_only")
        for view in self._queue_views():
            if hasattr(view, "mark_members_only"):
                view.mark_members_only(index, title)
            else:
                view.mark_cancelled(index, title)

        if hasattr(self.main_window, "library_panel"):
            self.main_window.library_panel.schedule_refresh(delay=0)

        self.log_panel.set_status("Mitglieder-Video übersprungen")
        self.update_status("Mitglieder-Video übersprungen")

    def on_current_download_item(self, title):
        self._public_download_status["current_title"] = str(title or "")
        if title:
            self.log_panel.set_status(f"Lädt gerade: {title}")
        else:
            self.log_panel.set_status("Warteschlange fertig")

    def cleanup_download_thread(self):
        if self.download_thread is not None:
            self.download_thread.deleteLater()

        self.download_thread = None
        self.download_worker = None

    def on_download_finished(self):
        self._public_download_status.update({
            "active": False,
            "status": "Warteschlange fertig",
            "current_title": "",
            "item_progress": 100,
            "total_progress": 100,
            "done_count": self._public_download_status.get("total_count", 0),
        })
        for view in self._queue_views():
            view.finish()

        if hasattr(self.main_window, "library_panel"):
            self.main_window.library_panel.refresh()
        if hasattr(self.main_window, "channel_panel"):
            self.main_window.channel_panel.update_current_info()

        self.log_panel.write("Warteschlange fertig.")
        self.log_panel.set_status("Warteschlange fertig")
        self.log_panel.set_progress(100)
        self.update_status("Download fertig")

    def on_download_error(self, error: str):
        self._public_download_status.update({"active": False, "status": f"Download-Fehler: {error}"})
        for view in self._queue_views():
            view.btn_cancel.setEnabled(False)

        self.log_panel.write(f"Download-Fehler: {error}")
        self.log_panel.set_status("Download-Fehler")
        self.update_status("Download-Fehler")