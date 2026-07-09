from src.mediahub.gui.video_load_dialog import VideoLoadDialog


class PreviewManager:
    def __init__(
        self,
        main_window,
        controller,
        youtube_service,
        archive_service,
        log_panel,
        update_status_callback,
        can_start_download_callback,
        open_video_selection_callback,
        playlist_service=None,
    ):
        self.main_window = main_window
        self.controller = controller
        self.youtube_service = youtube_service
        self.archive_service = archive_service
        self.log_panel = log_panel
        self.update_status = update_status_callback
        self.can_start_download = can_start_download_callback
        self.open_video_selection = open_video_selection_callback
        self.playlist_service = playlist_service
        self.repository = getattr(controller, "repository", None)

    def preview_current_channel(self):
        channel = self.controller.get_current_channel()

        if channel is None:
            self.log_panel.write("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return

        if not channel.url:
            self.log_panel.write("Der ausgewählte Kanal hat keine URL.")
            self.update_status("Keine Kanal-URL")
            return

        self.log_panel.write(f"Vorschau wird geladen: {channel.name}")
        self.update_status("Vorschau läuft")

        try:
            videos = None

            if self.has_active_playlist_settings(channel):
                self.log_panel.write("Aktive Playlists gefunden. Vorschau lädt mehrere Playlists.")
                videos = self.load_active_playlist_videos(channel, limit=10)
            else:
                video_url = self.to_videos_url(channel.url)
                self.log_panel.write(f"Quelle: {video_url}")
                videos = self.youtube_service.preview_channel(video_url, limit=10)
                videos = self.add_default_playlist_info(channel, videos)

            videos = self.archive_service.mark_videos(channel, videos)

            if not videos:
                self.log_panel.write("Keine Videos gefunden.")
                self.update_status("Keine Videos gefunden")
                return

            self.log_panel.write(f"{len(videos)} Videos gefunden:")

            for index, video in enumerate(videos, start=1):
                self.log_panel.write(
                    f"{index}. [{video.get('status', 'Neu')}] "
                    f"{video.get('playlist', channel.name)}: {video.get('title', 'Ohne Titel')}"
                )

            self.update_status("Vorschau fertig")

        except Exception as error:
            self.log_panel.write(f"Fehler bei Vorschau: {error}")
            self.update_status("Fehler bei Vorschau")

    def select_and_download_videos(self):
        channel = self.controller.get_current_channel()

        if channel is None:
            self.log_panel.write("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return

        if not channel.url:
            self.log_panel.write("Der ausgewählte Kanal hat keine URL.")
            self.update_status("Keine Kanal-URL")
            return

        if not self.can_start_download():
            self.log_panel.write(
                "Download kann nicht gestartet werden. Bitte prüfe Tool-Center, Arbeitsordner und Zielordner."
            )
            self.update_status("Download nicht bereit")
            return

        load_dialog = VideoLoadDialog(self.main_window)

        if not load_dialog.exec():
            self.log_panel.write("Videoliste abgebrochen.")
            self.update_status("Bereit")
            return

        self.log_panel.write(f"Lade Videoliste für Auswahl: {channel.name}")
        self.update_status("Videoliste wird geladen")

        try:
            if self.has_active_playlist_settings(channel):
                self.log_panel.write("Aktive Playlists gefunden. Es werden alle aktiven Playlists geladen.")
                videos = self.load_active_playlist_videos(
                    channel,
                    limit=load_dialog.selected_limit,
                )
            else:
                video_url = self.to_videos_url(channel.url)
                self.log_panel.write(f"Quelle: {video_url}")
                videos = self.youtube_service.preview_channel(
                    video_url,
                    limit=load_dialog.selected_limit
                )
                videos = self.add_default_playlist_info(channel, videos)

            videos = self.archive_service.mark_videos(channel, videos)

            if not videos:
                self.log_panel.write("Keine Videos für die Auswahl gefunden.")
                self.update_status("Keine Videos gefunden")
                return

            self.open_video_selection(channel, videos)

        except Exception as error:
            self.log_panel.write(f"Fehler bei Videoauswahl: {error}")
            self.update_status("Fehler bei Videoauswahl")

    def has_active_playlist_settings(self, channel) -> bool:
        settings = getattr(channel, "playlist_settings", []) or []
        return any(
            setting.get("enabled", True) and setting.get("url")
            for setting in settings
        )

    def load_active_playlist_videos(self, channel, limit=None) -> list[dict]:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        active_settings = [
            setting for setting in (getattr(channel, "playlist_settings", []) or [])
            if setting.get("enabled", True) and setting.get("url")
        ]

        all_videos = []
        seen_ids = set()
        valid_settings = []
        jobs = []
        skipped_bad = 0

        for index, setting in enumerate(active_settings, start=1):
            playlist_title = setting.get("playlist_name") or setting.get("title") or "Ohne Titel"
            display_name = setting.get("display_name") or playlist_title
            season = int(setting.get("season", index) or index)
            playlist_url = setting.get("url", "")

            if hasattr(self.youtube_service, "normalize_playlist_url"):
                fixed_url = self.youtube_service.normalize_playlist_url(playlist_url or setting.get("playlist_id", ""))
                if not fixed_url:
                    skipped_bad += 1
                    self.log_panel.write(f"Ungültige Playlist übersprungen: {playlist_title} ({playlist_url})")
                    continue
                playlist_url = fixed_url
                setting["url"] = fixed_url
                if hasattr(self.youtube_service, "_playlist_id_from_value"):
                    setting["playlist_id"] = self.youtube_service._playlist_id_from_value(fixed_url)

            setting["playlist_name"] = playlist_title
            setting["title"] = playlist_title
            valid_settings.append(setting)
            jobs.append({
                "index": len(valid_settings),
                "setting": setting,
                "playlist_title": playlist_title,
                "display_name": display_name,
                "season": season,
                "url": playlist_url,
                "kind": "playlist",
            })

        # Zusätzlich normale Kanalvideos laden. Das bleibt richtig so: Playlists + Kanalvideos.
        if channel.url:
            jobs.append({
                "index": len(valid_settings) + 1,
                "setting": {},
                "playlist_title": "Kanalvideos",
                "display_name": "Kanalvideos",
                "season": 1,
                "url": self.youtube_service.to_videos_url(channel.url) if hasattr(self.youtube_service, "to_videos_url") else channel.url,
                "kind": "channel",
            })

        if skipped_bad:
            self.log_panel.write(f"{skipped_bad} ungültige gespeicherte Playlist(s) entfernt/ignoriert.")
            try:
                channel.playlist_settings = valid_settings
            except Exception:
                pass

        if not jobs:
            return []

        self.log_panel.write(
            f"Lade {len(valid_settings)} Playlist(s) + Kanalvideos schneller im Hintergrund ..."
        )
        self.update_status("Videos werden geladen")

        results = []
        max_workers = min(5, max(1, len(jobs)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self.youtube_service.extract_videos, job["url"], limit): job
                for job in jobs
            }
            for future in as_completed(future_map):
                job = future_map[future]
                try:
                    videos = future.result() or []
                except Exception as error:
                    self.log_panel.write(f"{job['playlist_title']} konnte nicht geladen werden: {error}")
                    videos = []
                results.append((job["index"], job, videos))

        for _, job, videos in sorted(results, key=lambda item: item[0]):
            setting = job["setting"]
            playlist_title = job["playlist_title"]
            display_name = job["display_name"]
            season = job["season"]
            kind = job["kind"]

            if setting is not None:
                setting["video_count"] = len(videos)

            if self.repository is not None:
                try:
                    self.repository.save_discovered_videos(channel.name, playlist_title, videos)
                except Exception as db_error:
                    self.log_panel.write(f"SQLite-Videoablage fehlgeschlagen: {db_error}")

            added = 0
            skipped_duplicates = 0
            for video in videos:
                video_id = video.get("id") or video.get("video_id") or ""
                if video_id and video_id in seen_ids:
                    skipped_duplicates += 1
                    continue
                if video_id:
                    seen_ids.add(video_id)

                if kind == "channel":
                    video["playlist"] = "Kanalvideos"
                    video["playlist_original"] = "Kanalvideos"
                    video["playlist_id"] = "channel_uploads"
                    video["playlist_season"] = 1
                    video["playlist_image"] = ""
                else:
                    video["playlist"] = display_name
                    video["playlist_original"] = playlist_title
                    video["playlist_id"] = setting.get("playlist_id", "")
                    video["playlist_season"] = season
                    video["playlist_image"] = setting.get("image_path", "") or setting.get("playlist_image", "")
                all_videos.append(video)
                added += 1

            if kind == "channel":
                self.log_panel.write(
                    f"Kanalvideos: {len(videos)} geprüft, {skipped_duplicates} schon in Playlists, {added} übernommen."
                )
            else:
                self.log_panel.write(
                    f"Playlist geladen: {playlist_title} → {display_name}: {len(videos)} gefunden, {added} übernommen."
                )

        self.controller.save()
        self.log_panel.write(
            f"Aktive Playlists + Kanalvideos fertig geladen: {len(all_videos)} Videos nach Dublettenfilter."
        )
        return all_videos

    def add_default_playlist_info(self, channel, videos):
        default_name = getattr(channel, "name", "Kanalvideos") or "Kanalvideos"

        for video in videos:
            if not video.get("playlist"):
                video["playlist"] = default_name

            if not video.get("playlist_original"):
                video["playlist_original"] = default_name

            if not video.get("playlist_id"):
                video["playlist_id"] = "channel_uploads"

            if not video.get("playlist_season"):
                video["playlist_season"] = 1

        return videos

    def to_videos_url(self, channel_url: str) -> str:
        # Nicht selbst basteln: YouTubeService normalisiert Handles, UC-IDs und Tabs.
        if hasattr(self.youtube_service, "to_videos_url"):
            return self.youtube_service.to_videos_url(channel_url)

        url = (channel_url or "").strip()
        if not url:
            return ""
        if "/videos" in url:
            return url
        for old in ("/playlists", "/featured", "/streams", "/shorts"):
            if old in url:
                return url.replace(old, "/videos")
        return url.rstrip("/") + "/videos"

