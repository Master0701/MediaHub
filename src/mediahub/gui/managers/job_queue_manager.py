class JobQueueManager:
    """Verwaltet und startet manuelle Jobs.

    v0.9.2 ist die erste Job-Engine-Stufe: Jobs können angelegt und manuell
    abgearbeitet werden. Automatische Scheduler-Läufe kommen später.
    """

    def __init__(
        self,
        repository=None,
        job_queue_panel=None,
        log_panel=None,
        update_status_callback=None,
        controller=None,
        sync_manager=None,
        main_window=None,
        refresh_callbacks=None,
    ):
        self.repository = repository
        self.job_queue_panel = job_queue_panel
        self.log_panel = log_panel
        self.update_status = update_status_callback or (lambda text: None)
        self.controller = controller
        self.sync_manager = sync_manager
        self.main_window = main_window
        self.refresh_callbacks = list(refresh_callbacks or [])

        if self.job_queue_panel is not None:
            self.job_queue_panel.set_execute_next_callback(self.run_next_pending_job)
            self.job_queue_panel.set_execute_selected_callback(self.run_selected_job)

    def add_sync_job_for_channel(self, channel):
        if self.repository is None:
            self._log("Job-Queue nicht verfügbar: keine Datenbank.")
            self.update_status("Keine Job-Queue")
            return None
        if channel is None:
            self._log("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return None

        job_id = self.repository.create_job(
            job_type="sync_channel",
            title=f"Kanal synchronisieren: {channel.name}",
            channel_name=channel.name,
            payload={"channel": channel.name, "action": "sync"},
        )
        self._log(f"Job angelegt: Kanal synchronisieren ({channel.name})")
        self.update_status("Sync-Job angelegt")
        self.refresh()
        return job_id


    def add_sync_download_job_for_channel(self, channel):
        """Legt einen Job an, der erst synchronisiert und danach neue Videos zur Auswahl öffnet."""
        if self.repository is None:
            self._log("Job-Queue nicht verfügbar: keine Datenbank.")
            self.update_status("Keine Job-Queue")
            return None
        if channel is None:
            self._log("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return None

        job_id = self.repository.create_job(
            job_type="sync_download_channel",
            title=f"Sync + Download-Auswahl: {channel.name}",
            channel_name=channel.name,
            payload={"channel": channel.name, "actions": ["sync", "download_selection"]},
            priority=70,
        )
        self._log(f"Job angelegt: Sync + Download-Auswahl ({channel.name})")
        self.update_status("Sync+Download-Job angelegt")
        self.refresh()
        return job_id


    def add_sync_auto_download_job_for_channel(self, channel):
        """Legt einen Job an, der synchronisiert und neue Videos direkt lädt."""
        if self.repository is None:
            self._log("Job-Queue nicht verfügbar: keine Datenbank.")
            self.update_status("Keine Job-Queue")
            return None
        if channel is None:
            self._log("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return None

        job_id = self.repository.create_job(
            job_type="sync_auto_download_channel",
            title=f"Sync + Auto-Download: {channel.name}",
            channel_name=channel.name,
            payload={"channel": channel.name, "actions": ["sync", "download_auto"]},
            priority=60,
        )
        self._log(f"Job angelegt: Sync + Auto-Download ({channel.name})")
        self.update_status("Sync+Auto-Download-Job angelegt")
        self.refresh()
        return job_id

    def add_download_job_for_channel(self, channel, video_count=0):
        if self.repository is None or channel is None:
            return None
        title = f"Download-Warteschlange: {channel.name}"
        if video_count:
            title += f" ({video_count} Videos)"
        job_id = self.repository.create_job(
            job_type="download_queue",
            title=title,
            channel_name=channel.name,
            payload={"channel": channel.name, "video_count": int(video_count or 0)},
        )
        self.refresh()
        return job_id

    def run_next_pending_job(self):
        if self.repository is None:
            self._log("Job-Queue nicht verfügbar: keine Datenbank.")
            self.update_status("Keine Job-Queue")
            return

        job = self.repository.get_next_pending_job()
        if not job:
            self._log("Keine wartenden Jobs vorhanden.")
            self.update_status("Keine wartenden Jobs")
            self.refresh()
            return

        self.run_job(job)

    def run_selected_job(self, job_id):
        if self.repository is None or not job_id:
            return
        job = self.repository.get_job(int(job_id))
        if not job:
            self._log(f"Job nicht gefunden: {job_id}")
            self.refresh()
            return
        self.run_job(job)

    def run_job(self, job):
        job_id = int(job.get("id"))
        job_type = job.get("job_type", "")
        title = job.get("title", "")

        if job.get("status") == "running":
            self._log(f"Job läuft bereits: {title}")
            return

        self.repository.update_job_status(job_id, "running")
        self.refresh()
        self._log(f"Job gestartet: {title}")
        self.update_status("Job läuft")

        try:
            if job_type == "sync_channel":
                self._run_sync_job(job)
            elif job_type == "sync_download_channel":
                self._run_sync_download_job(job)
            elif job_type == "sync_auto_download_channel":
                self._run_sync_auto_download_job(job)
            elif job_type == "download_queue":
                # Download-Jobs dokumentieren aktuell gestartete Downloads. Die
                # echte Download-Queue läuft weiter über den stabilen DownloadManager.
                self._log("Download-Job ist aktuell ein Protokolleintrag. Downloads laufen über die Download-Warteschlange.")
            else:
                raise ValueError(f"Unbekannter Job-Typ: {job_type}")

            self.repository.update_job_status(job_id, "done")
            self._log(f"Job fertig: {title}")
            self.update_status("Job fertig")

        except Exception as error:
            self.repository.update_job_status(job_id, "failed", str(error))
            self._log(f"Job fehlgeschlagen: {title} | {error}")
            self.update_status("Job fehlgeschlagen")

        self._refresh_everything()

    def _run_sync_job(self, job):
        if self.sync_manager is None:
            raise RuntimeError("SyncManager ist nicht verfügbar")
        channel_name = job.get("channel_name", "")
        if not channel_name:
            raise RuntimeError("Job enthält keinen Kanalnamen")

        result = self.sync_manager.sync_channel_by_name(channel_name)
        failed = int(result.get("failed", 0) or 0)
        if failed:
            raise RuntimeError(f"Sync mit {failed} Playlist-Fehler(n) abgeschlossen")


    def _run_sync_download_job(self, job):
        """Sync ausführen und danach die neue Videoauswahl öffnen.

        Der eigentliche Download startet weiterhin erst nach Bestätigung im
        VideoSelectionDialog. Dadurch bleibt die Automatik sicher testbar und
        nutzt exakt den stabilen DownloadManager-Pfad.
        """
        channel_name = job.get("channel_name", "")
        if not channel_name:
            raise RuntimeError("Job enthält keinen Kanalnamen")
        if self.main_window is None:
            raise RuntimeError("MainWindow ist für Sync+Download nicht verfügbar")

        channel = None
        if self.controller is not None:
            for candidate in self.controller.get_channels():
                if candidate.name == channel_name:
                    channel = candidate
                    break
        if channel is None:
            raise RuntimeError(f"Kanal nicht gefunden: {channel_name}")

        self.main_window.sync_and_download_new_for_channel(channel)


    def _run_sync_auto_download_job(self, job):
        """Sync ausführen und neue Videos direkt in die Download-Warteschlange geben."""
        channel_name = job.get("channel_name", "")
        if not channel_name:
            raise RuntimeError("Job enthält keinen Kanalnamen")
        if self.main_window is None:
            raise RuntimeError("MainWindow ist für Sync+Auto-Download nicht verfügbar")

        channel = None
        if self.controller is not None:
            for candidate in self.controller.get_channels():
                if candidate.name == channel_name:
                    channel = candidate
                    break
        if channel is None:
            raise RuntimeError(f"Kanal nicht gefunden: {channel_name}")

        self.main_window.sync_and_auto_download_new_for_channel(channel)

    def refresh(self):
        if self.job_queue_panel is not None:
            self.job_queue_panel.refresh()

    def _refresh_everything(self):
        self.refresh()
        for callback in self.refresh_callbacks:
            try:
                callback()
            except Exception as error:
                self._log(f"Aktualisierung nach Job fehlgeschlagen: {error}")

    def _log(self, text):
        if self.log_panel is not None:
            self.log_panel.write(text)
