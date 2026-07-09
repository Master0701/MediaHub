from PySide6.QtCore import QTimer


class SchedulerManager:
    """Scheduler-Baustein mit kontrollierter Automatik.

    v0.9.4 prüft automatisch in festen Abständen, ob Aufgaben fällig sind.
    Fällige Aufgaben erzeugen weiterhin nur Jobs; die eigentliche Arbeit läuft
    über die Job-Queue. Dadurch bleibt der Scheduler sauber vom Sync/Download
    getrennt.
    """

    def __init__(
        self,
        repository=None,
        log_panel=None,
        job_queue_manager=None,
        scheduler_panel=None,
        controller=None,
        update_status_callback=None,
        recovery_manager=None,
    ):
        self.repository = repository
        self.log_panel = log_panel
        self.job_queue_manager = job_queue_manager
        self.scheduler_panel = scheduler_panel
        self.controller = controller
        self.recovery_manager = recovery_manager
        self.update_status = update_status_callback or (lambda text: None)
        self.auto_enabled = True
        self.auto_run_jobs = True
        self.check_interval_ms = 60_000
        self._is_checking = False

        self.timer = QTimer()
        self.timer.setInterval(self.check_interval_ms)
        self.timer.timeout.connect(self.check_due_tasks_automatically)

        self.start_automatic_checks(initial=True)

        if self.scheduler_panel is not None:
            self.scheduler_panel.set_callbacks(
                add_current_channel_callback=self.add_sync_task_for_current_channel,
                add_current_channel_sync_download_callback=self.add_sync_download_task_for_current_channel,
                add_current_channel_sync_auto_download_callback=self.add_sync_auto_download_task_for_current_channel,
                create_due_jobs_callback=self.create_due_jobs,
                run_selected_now_callback=self.create_job_for_task,
                delete_selected_callback=self.delete_task,
                toggle_automatic_callback=self.toggle_automatic_checks,
                check_now_callback=self.check_due_tasks_automatically,
                status_provider=self.get_automatic_status,
            )

    def is_available(self) -> bool:
        return self.repository is not None and self.job_queue_manager is not None

    def describe_next_step(self) -> str:
        return "Scheduler aktiv: Aufgaben erzeugen automatisch Jobs."

    def start_automatic_checks(self, initial=False):
        if not self.auto_enabled:
            return
        if not self.timer.isActive():
            self.timer.start()
        if initial:
            # Der erste automatische Lauf kommt leicht verzögert, damit das
            # Hauptfenster vollständig aufgebaut ist. Danach läuft der normale
            # 60-Sekunden-Takt.
            QTimer.singleShot(15_000, self.check_due_tasks_automatically)

    def stop_automatic_checks(self):
        if self.timer.isActive():
            self.timer.stop()

    def toggle_automatic_checks(self):
        self.auto_enabled = not self.auto_enabled
        if self.auto_enabled:
            self.start_automatic_checks()
            self._log("Scheduler-Automatik aktiviert.")
            self.update_status("Scheduler-Automatik aktiv")
        else:
            self.stop_automatic_checks()
            self._log("Scheduler-Automatik pausiert.")
            self.update_status("Scheduler pausiert")
        self.refresh()
        return self.auto_enabled

    def get_automatic_status(self) -> str:
        if self.auto_enabled and self.timer.isActive():
            return "Automatik: aktiv"
        if self.auto_enabled:
            return "Automatik: wartet"
        return "Automatik: pausiert"

    def check_due_tasks_automatically(self):
        if not self.auto_enabled or self._is_checking:
            return 0
        self._is_checking = True
        try:
            created = self.create_due_jobs(silent=True)
            if created and self.auto_run_jobs and self.job_queue_manager is not None:
                self.job_queue_manager.run_next_pending_job()
            return created
        finally:
            self._is_checking = False

    def add_sync_task_for_current_channel(self, interval_hours=24):
        if self.controller is None:
            self._log("Scheduler: Kein Controller verfügbar.")
            return None
        channel = self.controller.get_current_channel()
        return self.add_sync_task_for_channel(channel, interval_hours)



    def add_sync_auto_download_task_for_current_channel(self, interval_hours=24):
        if self.controller is None:
            self._log("Scheduler: Kein Controller verfügbar.")
            return None
        channel = self.controller.get_current_channel()
        return self.add_sync_auto_download_task_for_channel(channel, interval_hours)

    def add_sync_auto_download_task_for_channel(self, channel, interval_hours=24):
        """Legt eine Aufgabe an: synchronisieren und neue Videos automatisch laden."""
        if self.repository is None:
            self._log("Scheduler nicht verfügbar: keine Datenbank.")
            self.update_status("Kein Scheduler")
            return None
        if channel is None:
            self._log("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return None

        interval_hours = int(interval_hours or 24)
        task_id = self.repository.create_scheduled_task(
            name=f"{channel.name}: Sync + Auto-Download",
            task_type="sync_auto_download_channel",
            channel_name=channel.name,
            interval_hours=interval_hours,
            payload={"channel": channel.name, "actions": ["sync", "download_auto", "nfo"]},
            enabled=True,
            next_run_at="",
        )
        self._log(f"Scheduler-Aufgabe angelegt: {channel.name} Sync + Auto-Download alle {interval_hours} Stunde(n).")
        self.update_status("Scheduler-Auto-Download angelegt")
        self.refresh()
        return task_id

    def add_sync_download_task_for_current_channel(self, interval_hours=24):
        if self.controller is None:
            self._log("Scheduler: Kein Controller verfügbar.")
            return None
        channel = self.controller.get_current_channel()
        return self.add_sync_download_task_for_channel(channel, interval_hours)

    def add_sync_download_task_for_channel(self, channel, interval_hours=24):
        """Legt eine Aufgabe an: synchronisieren und neue Videos zur Download-Auswahl öffnen."""
        if self.repository is None:
            self._log("Scheduler nicht verfügbar: keine Datenbank.")
            self.update_status("Kein Scheduler")
            return None
        if channel is None:
            self._log("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return None

        interval_hours = int(interval_hours or 24)
        task_id = self.repository.create_scheduled_task(
            name=f"{channel.name}: Sync + Download-Auswahl",
            task_type="sync_download_channel",
            channel_name=channel.name,
            interval_hours=interval_hours,
            payload={"channel": channel.name, "actions": ["sync", "download_selection"]},
            enabled=True,
            next_run_at="",
        )
        self._log(f"Scheduler-Aufgabe angelegt: {channel.name} Sync + Download-Auswahl alle {interval_hours} Stunde(n).")
        self.update_status("Scheduler-Automation angelegt")
        self.refresh()
        return task_id

    def add_sync_task_for_channel(self, channel, interval_hours=24):
        if self.repository is None:
            self._log("Scheduler nicht verfügbar: keine Datenbank.")
            self.update_status("Kein Scheduler")
            return None
        if channel is None:
            self._log("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return None

        interval_hours = int(interval_hours or 24)
        task_id = self.repository.create_scheduled_task(
            name=f"{channel.name} automatisch synchronisieren",
            task_type="sync_channel",
            channel_name=channel.name,
            interval_hours=interval_hours,
            payload={"channel": channel.name, "action": "sync"},
            enabled=True,
            next_run_at="",
        )
        self._log(f"Scheduler-Aufgabe angelegt: {channel.name} alle {interval_hours} Stunde(n).")
        self.update_status("Scheduler-Aufgabe angelegt")
        self.refresh()
        return task_id

    def create_due_jobs(self, silent=False):
        if self.repository is None:
            self._log("Scheduler nicht verfügbar: keine Datenbank.")
            return 0

        tasks = self.repository.get_due_scheduled_tasks(limit=100)
        created = 0
        for task in tasks:
            if self._create_job_from_task(task):
                self.repository.mark_scheduled_task_run(int(task.get("id")))
                created += 1

        if created or not silent:
            self._log(f"Scheduler: {created} fällige Job(s) erzeugt.")
            self.update_status(f"{created} Scheduler-Job(s)")
        self.refresh_all()
        return created

    def create_job_for_task(self, task_id):
        if self.repository is None:
            return None
        task = self.repository.get_scheduled_task(int(task_id))
        if not task:
            self._log(f"Scheduler-Aufgabe nicht gefunden: {task_id}")
            self.refresh()
            return None
        job_id = self._create_job_from_task(task, force=True)
        if job_id:
            self.repository.mark_scheduled_task_run(int(task_id))
            self._log(f"Scheduler: Job aus Aufgabe erzeugt: {task.get('name', '')}")
            self.update_status("Scheduler-Job erzeugt")
        self.refresh_all()
        return job_id

    def delete_task(self, task_id):
        if self.repository is None:
            return
        self.repository.delete_scheduled_task(int(task_id))
        self._log(f"Scheduler-Aufgabe gelöscht: {task_id}")
        self.update_status("Scheduler-Aufgabe gelöscht")
        self.refresh()

    def _create_job_from_task(self, task, force=False):
        if self.repository is None:
            return None
        task_type = task.get("task_type", "")
        channel_name = task.get("channel_name", "")

        if task_type == "backup":
            if self.recovery_manager is None:
                self._log("Scheduler: Backup-Aufgabe kann nicht ausgeführt werden, Recovery Manager fehlt.")
                return None
            result = self.recovery_manager.create_backup(
                name="AutoBackup",
                comment="Automatisch vom Scheduler erstellt",
                include_database=True,
                include_config=True,
                include_logs=False,
                include_downloads=False,
            )
            self._log(f"Scheduler: Auto-Backup erstellt: {result.get('path')}")
            self.update_status("Auto-Backup erstellt")
            return -1

        if task_type not in {"sync_channel", "sync_download_channel", "sync_auto_download_channel"}:
            self._log(f"Scheduler: Unbekannter Aufgabentyp: {task_type}")
            return None
        if not channel_name:
            self._log("Scheduler: Aufgabe enthält keinen Kanalnamen.")
            return None

        if task_type == "sync_download_channel":
            return self.repository.create_job(
                job_type="sync_download_channel",
                title=f"Geplanter Sync + Download-Auswahl: {channel_name}",
                channel_name=channel_name,
                payload={"channel": channel_name, "source": "scheduler", "force": bool(force), "actions": ["sync", "download_selection"]},
                scheduled_at=task.get("next_run_at", "") or "",
                priority=70,
            )

        if task_type == "sync_auto_download_channel":
            return self.repository.create_job(
                job_type="sync_auto_download_channel",
                title=f"Geplanter Sync + Auto-Download: {channel_name}",
                channel_name=channel_name,
                payload={"channel": channel_name, "source": "scheduler", "force": bool(force), "actions": ["sync", "download_auto", "nfo"]},
                scheduled_at=task.get("next_run_at", "") or "",
                priority=60,
            )

        return self.repository.create_job(
            job_type="sync_channel",
            title=f"Geplanter Sync: {channel_name}",
            channel_name=channel_name,
            payload={"channel": channel_name, "source": "scheduler", "force": bool(force)},
            scheduled_at=task.get("next_run_at", "") or "",
            priority=80,
        )

    def refresh(self):
        if self.scheduler_panel is not None:
            self.scheduler_panel.refresh()

    def refresh_all(self):
        self.refresh()
        if self.job_queue_manager is not None:
            self.job_queue_manager.refresh()

    def _log(self, text):
        if self.log_panel is not None:
            self.log_panel.write(text)
