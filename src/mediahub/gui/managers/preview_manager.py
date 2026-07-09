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
        active_settings = [
            setting
            for setting in (getattr(channel, "playlist_settings", []) or [])
            if setting.get("enabled", True) and setting.get("url")
        ]

        all_videos = []
        seen_ids = set()

        for index, setting in enumerate(active_settings, start=1):
            playlist_title = setting.get("playlist_name", "Ohne Titel")
            display_name = setting.get("display_name") or playlist_title
            season = int(setting.get("season", index) or index)
            playlist_url = setting.get("url", "")

            self.log_panel.write(
                f"Lade aktive Playlist {index}/{len(active_settings)}: "
                f"{playlist_title} → {display_name} | Staffel {season}"
            )
            self.update_status(f"Playlist {index}/{len(active_settings)} wird geladen")

            videos = self.youtube_service.extract_videos(playlist_url, limit=limit)
            setting["video_count"] = len(videos)

            if self.repository is not None:
                try:
                    self.repository.save_discovered_videos(channel.name, playlist_title, videos)
                except Exception as db_error:
                    self.log_panel.write(f"SQLite-Videoablage fehlgeschlagen: {db_error}")

            added = 0
            for video in videos:
                video_id = video.get("id") or video.get("video_id") or ""
                if video_id and video_id in seen_ids:
                    continue

                if video_id:
                    seen_ids.add(video_id)

                video["playlist"] = display_name
                video["playlist_original"] = playlist_title
                video["playlist_id"] = setting.get("playlist_id", "")
                video["playlist_season"] = season
                video["playlist_image"] = setting.get("image_path", "") or setting.get("playlist_image", "")
                all_videos.append(video)
                added += 1

            self.log_panel.write(
                f"{len(videos)} Videos gefunden, {added} neue Einträge übernommen."
            )

        # Zusätzlich normale Kanalvideos laden.
        # Playlists behalten Vorrang: IDs, die schon in Playlists vorkommen, werden übersprungen.
        try:
            self.log_panel.write("Lade zusätzliche Kanalvideos außerhalb von Playlists ...")
            channel_videos = self.youtube_service.get_channel_videos(channel.url, limit=limit)
            added_channel = 0
            skipped_duplicates = 0

            for video in channel_videos:
                video_id = video.get("id") or video.get("video_id") or ""
                if video_id and video_id in seen_ids:
                    skipped_duplicates += 1
                    continue

                if video_id:
                    seen_ids.add(video_id)

                video["playlist"] = "📺 Kanalvideos"
                video["playlist_original"] = "📺 Kanalvideos"
                video["playlist_id"] = "channel_uploads"
                video["playlist_season"] = 1
                video["playlist_image"] = ""
                all_videos.append(video)
                added_channel += 1

            if self.repository is not None and added_channel:
                try:
                    self.repository.save_discovered_videos(channel.name, "📺 Kanalvideos", [
                        video for video in all_videos if video.get("playlist_id") == "channel_uploads"
                    ])
                except Exception as db_error:
                    self.log_panel.write(f"SQLite-Ablage für Kanalvideos fehlgeschlagen: {db_error}")

            self.log_panel.write(
                f"📺 Kanalvideos: {len(channel_videos)} geprüft, "
                f"{skipped_duplicates} schon in Playlists, {added_channel} übernommen."
            )
        except Exception as error:
            self.log_panel.write(f"Kanalvideos konnten nicht geladen werden: {error}")

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
        url = (channel_url or "").strip()

        if not url:
            return ""

        if "/videos" in url:
            return url

        if "/playlists" in url:
            return url.replace("/playlists", "/videos")

        if "/featured" in url:
            return url.replace("/featured", "/videos")

        if "/streams" in url:
            return url.replace("/streams", "/videos")

        if "/shorts" in url:
            return url.replace("/shorts", "/videos")

        return url.rstrip("/") + "/videos"
