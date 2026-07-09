CHANNEL_VIDEOS_TITLE = "📺 Kanalvideos"


class SyncManager:
    """Synchronisiert aktive Playlists und kanalweite Videos in SQLite.

    Playlists haben Priorität: Wenn ein Video sowohl in einer Playlist als
    auch im normalen Videos-Reiter eines Kanals auftaucht, wird es nur über
    die Playlist übernommen. Unter "📺 Kanalvideos" landen nur Videos, die
    in keiner aktiven Playlist gefunden wurden.
    """

    def __init__(
        self,
        main_window,
        controller,
        youtube_service,
        repository,
        log_panel,
        update_status_callback,
    ):
        self.main_window = main_window
        self.controller = controller
        self.youtube_service = youtube_service
        self.repository = repository
        self.log_panel = log_panel
        self.update_status = update_status_callback

    def sync_current_channel(self):
        return self.sync_channel(self.controller.get_current_channel())

    def sync_channel_by_name(self, channel_name: str):
        for channel in self.controller.get_channels():
            if channel.name == channel_name:
                return self.sync_channel(channel)
        raise ValueError(f"Kanal nicht gefunden: {channel_name}")

    def sync_channel(self, channel):
        if channel is None:
            self.log_panel.write("Kein Kanal ausgewählt.")
            self.update_status("Kein Kanal ausgewählt")
            return {"ok": False, "seen": 0, "new": 0, "updated": 0, "failed": 0}

        settings = [
            setting
            for setting in (getattr(channel, "playlist_settings", []) or [])
            if setting.get("enabled", True) and setting.get("url")
        ]

        if self.repository is None:
            self.log_panel.write("SQLite-Datenbank ist nicht verfügbar.")
            self.update_status("Keine Datenbank")
            return {"ok": False, "seen": 0, "new": 0, "updated": 0, "failed": 0}

        self.log_panel.write(f"Synchronisierung gestartet: {channel.name}")
        self.log_panel.write(f"Aktive Playlists: {len(settings)}")
        self.update_status("Synchronisierung läuft")

        total_seen = 0
        total_new = 0
        total_updated = 0
        failed = 0
        playlist_video_ids = set()

        for index, setting in enumerate(settings, start=1):
            playlist_title = setting.get("playlist_name", "Ohne Titel")
            playlist_url = setting.get("url", "")

            self.log_panel.write(
                f"Prüfe Playlist {index}/{len(settings)}: {playlist_title}"
            )
            self.update_status(f"Sync Playlist {index}/{len(settings)}")

            try:
                videos = self.youtube_service.extract_videos(playlist_url, limit=None)
                playlist_video_ids.update(self._video_ids(videos))

                result = self.repository.save_discovered_videos(
                    channel.name,
                    playlist_title,
                    videos,
                    mark_new=True,
                )

                setting["video_count"] = result.get("seen", len(videos))
                setting["new_video_count"] = result.get("new", 0)
                total_seen += result.get("seen", len(videos))
                total_new += result.get("new", 0)
                total_updated += result.get("updated", 0)

                self.log_panel.write(
                    f"{playlist_title}: {result.get('seen', len(videos))} Videos, "
                    f"{result.get('new', 0)} neu, {result.get('updated', 0)} bekannt, "
                    f"{result.get('linked', 0)} Playlist-Zuordnungen."
                )

            except Exception as error:
                failed += 1
                self.log_panel.write(f"Fehler bei Playlist '{playlist_title}': {error}")

        channel_video_result = self._sync_channel_videos(channel, playlist_video_ids)
        total_seen += channel_video_result.get("seen", 0)
        total_new += channel_video_result.get("new", 0)
        total_updated += channel_video_result.get("updated", 0)
        failed += channel_video_result.get("failed", 0)

        self.controller.save()

        stats = self.repository.get_channel_video_stats(channel.name)
        self.log_panel.write(
            "Synchronisierung fertig: "
            f"{total_seen} geprüft, {total_new} neu, {total_updated} bekannt, "
            f"{failed} Fehler. Datenbank: {stats.get('videos', 0)} Videos gesamt, "
            f"{stats.get('new_videos', 0)} neue markiert."
        )
        self.update_status("Synchronisierung fertig")
        return {
            "ok": failed == 0,
            "seen": total_seen,
            "new": total_new,
            "updated": total_updated,
            "failed": failed,
        }

    def _sync_channel_videos(self, channel, playlist_video_ids: set[str]) -> dict:
        result = {"seen": 0, "new": 0, "updated": 0, "failed": 0}

        try:
            self.log_panel.write("Prüfe Kanalvideos außerhalb von Playlists ...")
            self.update_status("Sync Kanalvideos")

            videos = self.youtube_service.get_channel_videos(channel.url, limit=None)
            filtered = []
            skipped_duplicates = 0

            for video in videos:
                video_id = self._video_id(video)
                if not video_id:
                    continue

                if video_id in playlist_video_ids:
                    skipped_duplicates += 1
                    continue

                video["playlist"] = CHANNEL_VIDEOS_TITLE
                filtered.append(video)

            save_result = self.repository.save_discovered_videos(
                channel.name,
                CHANNEL_VIDEOS_TITLE,
                filtered,
                mark_new=True,
            )

            result["seen"] = save_result.get("seen", len(filtered))
            result["new"] = save_result.get("new", 0)
            result["updated"] = save_result.get("updated", 0)

            self.log_panel.write(
                f"{CHANNEL_VIDEOS_TITLE}: {len(videos)} Kanalvideos geprüft, "
                f"{skipped_duplicates} bereits über Playlists vorhanden, "
                f"{save_result.get('seen', len(filtered))} übernommen, "
                f"{save_result.get('new', 0)} neu."
            )

        except Exception as error:
            result["failed"] = 1
            self.log_panel.write(f"Fehler bei Kanalvideos: {error}")

        return result

    def _video_ids(self, videos: list[dict]) -> set[str]:
        return {video_id for video_id in (self._video_id(video) for video in videos) if video_id}

    def _video_id(self, video: dict) -> str:
        return str(video.get("id") or video.get("video_id") or "").strip()
