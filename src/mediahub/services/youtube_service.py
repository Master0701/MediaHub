import re

from yt_dlp import YoutubeDL


class YouTubeService:
    def preview_channel(self, url: str, limit=None) -> list[dict]:
        return self.extract_videos(url, limit)

    def get_channel_info(self, channel_url: str) -> dict:
        if not channel_url:
            return {}

        options = {
            "quiet": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "skip_download": True,
        }

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(channel_url, download=False)

        if not info:
            return {}

        thumbnails = info.get("thumbnails", []) or []
        thumbnail_url = ""

        if thumbnails:
            thumbnail_url = thumbnails[-1].get("url", "")

        banner_url = self._best_image_url(
            info.get("banners", [])
            or info.get("banner", [])
            or info.get("channel_banners", [])
            or []
        )

        title = (
            info.get("channel")
            or info.get("uploader")
            or info.get("title")
            or ""
        )

        channel_id = (
            info.get("channel_id")
            or info.get("uploader_id")
            or info.get("id")
            or ""
        )

        real_url = (
            info.get("channel_url")
            or info.get("uploader_url")
            or info.get("webpage_url")
            or channel_url
        )

        description = (
            info.get("description")
            or info.get("channel_description")
            or ""
        )

        return {
            "id": channel_id,
            "name": title,
            "url": real_url,
            "description": description,
            "avatar": thumbnail_url,
            "banner": banner_url,
            "raw": info,
        }

    def extract_videos(self, url: str, limit=None) -> list[dict]:
        if not url:
            return []

        options = {
            "quiet": True,
            "extract_flat": True,
            "ignoreerrors": True,
        }

        if limit is not None:
            options["playlistend"] = int(limit)

        videos = []

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        entries = info.get("entries", []) if info else []

        for entry in entries:
            video = self._entry_to_video(entry)
            if video is not None:
                videos.append(video)

        return videos

    def get_channel_videos(self, channel_url: str, limit=None) -> list[dict]:
        """Liest den normalen Videos-Reiter eines Kanals.

        Dieser Bereich enthält oft Videos, die in keiner Playlist liegen.
        Playlists werden separat behandelt; doppelte Video-IDs werden später
        im SyncManager gefiltert, damit Playlist-Zuordnungen Vorrang haben.
        """
        if not channel_url:
            return []

        return self.extract_videos(self.to_videos_url(channel_url), limit=limit)

    def get_playlists(self, channel_url: str) -> list[dict]:
        if not channel_url:
            return []

        playlists_url = self.to_playlists_url(channel_url)

        options = {
            "quiet": True,
            "extract_flat": True,
            "ignoreerrors": True,
        }

        playlists = []

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(playlists_url, download=False)

        entries = info.get("entries", []) if info else []

        for entry in entries:
            if not entry:
                continue

            playlist_id = entry.get("id", "")
            title = entry.get("title", "Ohne Titel")

            url = entry.get("url", "")
            if playlist_id and not str(url).startswith("http"):
                url = f"https://www.youtube.com/playlist?list={playlist_id}"

            thumbnail_url = self._best_image_url(entry.get("thumbnails", []) or [])

            playlists.append({
                "id": playlist_id,
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "thumbnail": thumbnail_url,
            })

        return playlists

    def get_playlist_video_count(self, playlist_url: str) -> int:
        if not playlist_url:
            return 0

        options = {
            "quiet": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "skip_download": True,
        }

        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
        except Exception:
            return 0

        if not info:
            return 0

        entries = info.get("entries", []) or []
        return len([entry for entry in entries if entry])

    def _best_image_url(self, images) -> str:
        if isinstance(images, str):
            return images

        if not isinstance(images, list):
            return ""

        for item in reversed(images):
            if isinstance(item, dict):
                url = item.get("url", "")
                if url:
                    return url
            elif isinstance(item, str) and item:
                return item

        return ""

    def to_playlists_url(self, channel_url: str) -> str:
        url = channel_url.strip()

        if "/videos" in url:
            return url.replace("/videos", "/playlists")

        if "/playlists" in url:
            return url

        return url.rstrip("/") + "/playlists"

    def to_videos_url(self, channel_url: str) -> str:
        url = channel_url.strip()

        if "/playlists" in url:
            return url.replace("/playlists", "/videos")

        if "/videos" in url:
            return url

        return url.rstrip("/") + "/videos"

    def _extract_video_id_from_url(self, value: str) -> str:
        text = str(value or "")
        patterns = (
            r"(?:v=|/watch\?v=)([A-Za-z0-9_-]{6,})",
            r"youtu\.be/([A-Za-z0-9_-]{6,})",
            r"/shorts/([A-Za-z0-9_-]{6,})",
            r"/embed/([A-Za-z0-9_-]{6,})",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ""

    def _best_title(self, entry: dict) -> str:
        for key in ("title", "fulltitle", "alt_title", "display_id"):
            value = str(entry.get(key) or "").strip()
            if value and value.lower() not in {"none", "null", "nan"}:
                return value
        return ""

    def _entry_to_video(self, entry: dict | None) -> dict | None:
        if not entry:
            return None

        entry_type = str(entry.get("_type") or entry.get("ie_key") or "").lower()
        raw_url = str(entry.get("webpage_url") or entry.get("url") or "").strip()

        if "playlist" in entry_type and not entry.get("duration") and "watch" not in raw_url:
            return None
        if entry_type in {"channel", "url", "url_transparent"} and not self._extract_video_id_from_url(raw_url):
            return None

        video_id = str(entry.get("id") or "").strip()
        url_video_id = self._extract_video_id_from_url(raw_url)
        if url_video_id:
            video_id = url_video_id

        webpage_url = raw_url
        if video_id and not webpage_url.startswith("http"):
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        elif video_id and "watch" not in webpage_url and "youtu.be" not in webpage_url and "shorts" not in webpage_url:
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"

        title = self._best_title(entry)
        if not title and not video_id:
            return None
        if not title:
            title = f"Video {video_id}"

        thumbnail_url = self._best_image_url(entry.get("thumbnails", []) or [])
        availability = entry.get("availability", "") or ""
        status = "Mitglieder/Abo" if self._looks_members_only(entry) else "Neu"

        return {
            "id": video_id,
            "video_id": video_id,
            "title": title,
            "url": webpage_url,
            "description": entry.get("description", "") or "",
            "thumbnail_url": thumbnail_url,
            "thumbnail": thumbnail_url,
            "upload_date": entry.get("upload_date", "") or "",
            "duration": entry.get("duration", 0) or 0,
            "view_count": entry.get("view_count", 0) or 0,
            "availability": availability,
            "is_members_only": 1 if self._looks_members_only(entry) else 0,
            "status": status,
        }

    def _looks_members_only(self, entry: dict | None) -> bool:
        if not entry:
            return False

        text = " ".join(
            str(entry.get(key, ""))
            for key in (
                "title", "availability", "status", "live_status",
                "message", "error", "description", "reason"
            )
        ).lower()

        markers = (
            "members-only",
            "members only",
            "member-only",
            "channel members",
            "mitglied",
            "kanalmitglied",
            "kanalmitgliedschaft",
            "abo-video",
            "subscriber-only",
            "subscribers only",
            "requires payment",
            "premium_only",
            "premium only",
            "private video",
            "join this channel",
        )
        return any(marker in text for marker in markers)
