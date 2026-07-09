class PlaylistService:
    def __init__(self, youtube_service):
        self.youtube_service = youtube_service

    def load_playlists(self, channel) -> list[dict]:
        playlists = self.youtube_service.get_playlists(channel.url)
        return playlists or []

    def sync_playlist_settings(self, channel, playlists: list[dict]) -> list[dict]:
        old_settings = getattr(channel, "playlist_settings", []) or []
        old_by_id = {}

        for setting in old_settings:
            playlist_id = setting.get("playlist_id", "")
            if playlist_id:
                old_by_id[playlist_id] = setting

        synced = []

        for index, playlist in enumerate(playlists, start=1):
            playlist_id = playlist.get("id", "")
            playlist_name = playlist.get("title", "Ohne Titel")
            playlist_url = playlist.get("url", "")
            thumbnail_url = playlist.get("thumbnail_url", playlist.get("thumbnail", ""))

            old = old_by_id.get(playlist_id, {})

            synced.append({
                "playlist_id": playlist_id,
                "playlist_name": playlist_name,
                "display_name": old.get("display_name", playlist_name),
                "season": int(old.get("season", index)),
                "enabled": bool(old.get("enabled", True)),
                "url": playlist_url,
                "video_count": int(old.get("video_count", playlist.get("video_count", 0)) or 0),
                "new_video_count": int(old.get("new_video_count", 0) or 0),
                "sort_order": int(old.get("sort_order", index) or index),
                "thumbnail_url": old.get("thumbnail_url", thumbnail_url),
                "image_path": old.get("image_path", playlist.get("image_path", "")),
            })

        return synced

    def get_active_playlist_settings(self, channel) -> list[dict]:
        settings = getattr(channel, "playlist_settings", []) or []
        return [
            setting
            for setting in settings
            if setting.get("enabled", True)
        ]

    def find_setting_for_playlist(self, channel, playlist: dict) -> dict:
        playlist_id = playlist.get("id", "")
        settings = getattr(channel, "playlist_settings", []) or []

        for setting in settings:
            if setting.get("playlist_id", "") == playlist_id:
                return setting

        return {}

    def prepare_playlist_for_download(self, playlist: dict, setting: dict) -> dict:
        playlist_name = playlist.get("title", "Ohne Titel")

        display_name = setting.get("display_name") or playlist_name
        season = int(setting.get("season", 1))
        enabled = bool(setting.get("enabled", True))

        return {
            "id": playlist.get("id", ""),
            "title": playlist_name,
            "display_name": display_name,
            "season": season,
            "enabled": enabled,
            "url": playlist.get("url", setting.get("url", "")),
            "video_count": int(setting.get("video_count", playlist.get("video_count", 0)) or 0),
            "sort_order": int(setting.get("sort_order", 0) or 0),
            "thumbnail_url": playlist.get("thumbnail_url", setting.get("thumbnail_url", "")),
            "image_path": playlist.get("image_path", setting.get("image_path", "")),
        }

    def prepare_active_playlists_for_download(self, channel, playlists: list[dict]) -> list[dict]:
        prepared = []

        for playlist in playlists:
            setting = self.find_setting_for_playlist(channel, playlist)

            if setting and not setting.get("enabled", True):
                continue

            prepared_playlist = self.prepare_playlist_for_download(playlist, setting)
            prepared.append(prepared_playlist)

        return prepared