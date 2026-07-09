from src.mediahub.gui.playlist_manager_dialog import PlaylistManagerDialog
from src.mediahub.gui.video_load_dialog import VideoLoadDialog


class PlaylistManager:
    def __init__(
        self,
        main_window,
        controller,
        youtube_service,
        playlist_service,
        archive_service,
        log_panel,
        update_status_callback,
        can_start_download_callback,
        open_video_selection_callback,
    ):
        self.main_window = main_window
        self.controller = controller
        self.youtube_service = youtube_service
        self.playlist_service = playlist_service
        self.archive_service = archive_service
        self.log_panel = log_panel
        self.update_status = update_status_callback
        self.can_start_download = can_start_download_callback
        self.open_video_selection = open_video_selection_callback
        self.repository = getattr(controller, "repository", None)

    def open_playlist_manager(self):
        channel = self.controller.get_current_channel()

        if channel is None:
            self.log_panel.write("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return

        self.log_panel.write(f"Lade Playlists für Playlist-Manager: {channel.name}")
        self.update_status("Playlist-Manager lädt")

        try:
            playlists = self.playlist_service.load_playlists(channel)

            if not playlists:
                self.log_panel.write("Keine Playlists gefunden.")
                self.update_status("Keine Playlists gefunden")
                return

            self.fill_playlist_video_counts(channel, playlists)

            channel.playlist_settings = self.playlist_service.sync_playlist_settings(
                channel,
                playlists
            )
            self.controller.save()

            dialog = PlaylistManagerDialog(channel, playlists, self.main_window)

            if not dialog.exec():
                self.log_panel.write("Playlist-Manager abgebrochen.")
                self.update_status("Bereit")
                return

            channel.playlist_settings = dialog.playlist_settings
            self.controller.save()

            self.log_panel.write(
                f"Playlist-Einstellungen gespeichert: "
                f"{len(channel.playlist_settings)} Playlists"
            )
            self.update_status("Playlist-Einstellungen gespeichert")

        except Exception as error:
            self.log_panel.write(f"Fehler im Playlist-Manager: {error}")
            self.update_status("Fehler im Playlist-Manager")

    def select_playlists_and_download(self):
        channel = self.controller.get_current_channel()

        if channel is None:
            self.log_panel.write("Kein Kanal ausgewählt.")
            return

        if not self.can_start_download():
            return

        self.log_panel.write(f"Lade Playlists aus Manager: {channel.name}")
        self.update_status("Manager-Playlists werden geladen")

        try:
            playlists = self.playlist_service.load_playlists(channel)

            if not playlists:
                self.log_panel.write("Keine Playlists gefunden.")
                self.update_status("Keine Playlists gefunden")
                return

            channel.playlist_settings = self.playlist_service.sync_playlist_settings(
                channel,
                playlists
            )
            self.controller.save()

            selected_playlists = self.playlist_service.prepare_active_playlists_for_download(
                channel,
                playlists
            )

            if not selected_playlists:
                self.log_panel.write("Keine aktive Playlist im Playlist-Manager gefunden.")
                self.update_status("Keine aktive Playlist")
                return

            self.log_panel.write(
                f"{len(selected_playlists)} aktive Playlists aus dem Playlist-Manager."
            )

            load_dialog = VideoLoadDialog(self.main_window)

            if not load_dialog.exec():
                self.log_panel.write("Videoliste abgebrochen.")
                self.update_status("Bereit")
                return

            all_videos = []

            for playlist in selected_playlists:
                playlist_title = playlist.get("title", "Ohne Titel")
                display_name = playlist.get("display_name", playlist_title)
                season = playlist.get("season", 1)

                self.log_panel.write(
                    f"Lade Playlist: {playlist_title} → Plex-Name: {display_name} | Staffel {season}"
                )

                videos = self.youtube_service.extract_videos(
                    playlist.get("url", ""),
                    limit=load_dialog.selected_limit
                )

                self.log_panel.write(
                    f"{len(videos)} Videos aus Playlist gefunden: {playlist_title}"
                )

                playlist["video_count"] = len(videos)

                if self.repository is not None:
                    try:
                        self.repository.save_discovered_videos(channel.name, playlist_title, videos)
                    except Exception as db_error:
                        self.log_panel.write(f"SQLite-Videoablage fehlgeschlagen: {db_error}")

                for video in videos:
                    video["playlist"] = display_name
                    video["playlist_original"] = playlist_title
                    video["playlist_id"] = playlist.get("id", "")
                    video["playlist_season"] = season

                all_videos.extend(videos)

            self.update_playlist_video_counts(channel, selected_playlists)
            self.controller.save()

            all_videos = self.archive_service.mark_videos(channel, all_videos)
            self.open_video_selection(channel, all_videos)

        except Exception as error:
            self.log_panel.write(f"Fehler bei Manager-Playlists: {error}")
            self.update_status("Fehler bei Manager-Playlists")
    def update_playlist_video_counts(self, channel, selected_playlists):
        counts_by_id = {
            playlist.get("id", ""): int(playlist.get("video_count", 0) or 0)
            for playlist in selected_playlists
        }

        for setting in getattr(channel, "playlist_settings", []) or []:
            playlist_id = setting.get("playlist_id", "")
            if playlist_id in counts_by_id:
                setting["video_count"] = counts_by_id[playlist_id]


    def fill_playlist_video_counts(self, channel, playlists):
        """Ermittelt und übernimmt Videoanzahlen für den Playlist-Manager.

        Zuerst werden gespeicherte Werte verwendet. Fehlt ein Wert, wird die
        Playlist kurz flach ausgelesen und die Anzahl übernommen.
        """
        old_counts = {}
        for setting in getattr(channel, "playlist_settings", []) or []:
            playlist_id = setting.get("playlist_id", "")
            count = int(setting.get("video_count", 0) or 0)
            if playlist_id and count > 0:
                old_counts[playlist_id] = count

        for index, playlist in enumerate(playlists, start=1):
            playlist_id = playlist.get("id", "")

            if int(playlist.get("video_count", 0) or 0) > 0:
                continue

            if playlist_id in old_counts:
                playlist["video_count"] = old_counts[playlist_id]
                continue

            self.update_status(f"Zähle Playlist {index}/{len(playlists)}")
            count = self.youtube_service.get_playlist_video_count(playlist.get("url", ""))
            if count > 0:
                playlist["video_count"] = count
