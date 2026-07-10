import re
import json
import urllib.request
from html import unescape

from yt_dlp import YoutubeDL


class YouTubeService:

    def __init__(self):
        # Teil 9 Fix 6: kleine Laufzeit-Zwischenspeicherung.
        # Dadurch werden gleiche yt-dlp-Abfragen in Assistent, Hauptfenster
        # und Videoauswahl nicht direkt mehrfach hintereinander neu geladen.
        self._info_cache = {}

    def clear_cache(self):
        self._info_cache = {}

    def _extract_info_cached(self, url: str, *, limit=None, cache_tag: str = "flat"):
        text_url = str(url or "").strip()
        if not text_url:
            return None

        key = (cache_tag, text_url, int(limit) if limit is not None else None)
        if key in self._info_cache:
            return self._info_cache[key]

        options = {
            "quiet": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "skip_download": True,
        }
        if limit is not None:
            options["playlistend"] = int(limit)

        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(text_url, download=False)
        except Exception:
            info = None

        # Cache begrenzen, damit lange Sessions nicht unnötig Speicher sammeln.
        if len(self._info_cache) > 80:
            self._info_cache.clear()
        self._info_cache[key] = info
        return info

    def normalize_channel_url(self, channel_url: str) -> str:
        """Macht aus Handle, Channel-ID oder alter Tab-URL eine saubere Kanal-URL.

        Wichtig für Teil 9:
        yt-dlp bekommt bei reinen IDs wie "UC..." sonst URLs wie
        "UC.../videos". Das endet mit youtube:tab HTTP 400 und zerlegt danach
        Wizard- und Hauptfenster-Videoauswahl.
        """
        url = str(channel_url or "").strip()
        if not url:
            return ""

        # Häufig gespeicherter Fehler: nur die UC-Channel-ID ohne Domain.
        if re.fullmatch(r"UC[A-Za-z0-9_-]{20,}", url):
            return f"https://www.youtube.com/channel/{url}"

        # Handle ohne Domain, z. B. @WCSInfokanal
        if url.startswith("@"):
            return f"https://www.youtube.com/{url}"

        # Handle ohne @/Domain nur als letzter sinnvoller Fallback.
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url) and "/" not in url:
            return f"https://www.youtube.com/@{url.lstrip('@')}"

        url = url.replace("m.youtube.com/", "www.youtube.com/")

        # Falls irgendwo nur youtube.com/channel/UC... ohne Schema steht.
        if url.startswith("www.youtube.com/") or url.startswith("youtube.com/"):
            url = "https://" + url

        for suffix in ("/videos", "/playlists", "/featured", "/streams", "/shorts", "/community"):
            if url.endswith(suffix):
                url = url[: -len(suffix)]
                break

        return url.rstrip("/")

    def preview_channel(self, url: str, limit=None) -> list[dict]:
        return self.extract_videos(url, limit)

    def get_channel_info(self, channel_url: str) -> dict:
        channel_url = self.normalize_channel_url(channel_url) if hasattr(self, "normalize_channel_url") else str(channel_url or "").strip()
        if not channel_url:
            return {}

        options = {
            "quiet": True,
            "extract_flat": True,
            "ignoreerrors": True,
            "skip_download": True,
        }

        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(channel_url, download=False)
        except Exception:
            return {}

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
        title = str(title or "").strip()
        if title.lower() in {"", "none", "null", "nan", "ohne titel", "untitled", "videos", "playlists", "featured"}:
            # Wichtig: leer zurückgeben, damit der Assistent sauber aus der URL
            # rät und nicht "Ohne Titel" als YouTube-Name übernimmt.
            title = ""

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
        if hasattr(self, "normalize_channel_url"):
            real_url = self.normalize_channel_url(real_url)

        about_info = self.get_channel_about_info(real_url)

        description = self._clean_channel_description(
            about_info.get("description")
            or info.get("channel_description")
            or info.get("uploader_description")
            or info.get("about")
            or info.get("description")
            or ""
        )

        # Wenn yt-dlp nur eine Videobeschreibung geliefert hat, lieber keine
        # falschen Werkzeug-/Videolinks in die Serien-NFO schreiben.
        if self._looks_like_video_description(description):
            description = self._clean_channel_description(about_info.get("description") or "")

        banner_url = banner_url or about_info.get("banner", "")

        return {
            "id": channel_id,
            "name": title,
            "url": real_url,
            "description": description,
            "channel_description": description,
            "links": about_info.get("links", []),
            "country": about_info.get("country", ""),
            "subscriber_count": about_info.get("subscriber_count", ""),
            "video_count": about_info.get("video_count", ""),
            "view_count": about_info.get("view_count", ""),
            "joined_date": about_info.get("joined_date", ""),
            "avatar": thumbnail_url,
            "banner": banner_url,
            "raw": info,
        }

    def get_channel_about_info(self, channel_url: str) -> dict:
        """Liest einfache Kanalinfos aus der YouTube-About-Seite.

        Diese Daten sind optional. Wenn YouTube die Seite ändert oder blockiert,
        bleibt MediaHub trotzdem funktionsfähig und verwendet nur yt-dlp-Daten.
        """
        result = {
            "description": "",
            "links": [],
            "banner": "",
            "country": "",
            "subscriber_count": "",
            "video_count": "",
            "view_count": "",
            "joined_date": "",
        }
        base = self.normalize_channel_url(channel_url)
        if not base:
            return result

        about_url = base.rstrip("/") + "/about"
        try:
            request = urllib.request.Request(
                about_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
                },
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                html = response.read().decode("utf-8", errors="replace")
        except Exception:
            return result

        data = self._extract_yt_initial_data(html)
        if data:
            text_values = []
            self._walk_json(data, text_values)

            description = self._find_about_description(text_values)
            if description:
                result["description"] = description

            links = self._find_about_links(data)
            if links:
                result["links"] = links

            banner = self._find_about_banner(data)
            if banner:
                result["banner"] = banner

            stats = self._find_about_stats(text_values)
            result.update({key: value for key, value in stats.items() if value})

        return result

    def _extract_yt_initial_data(self, html: str):
        marker = "ytInitialData = "
        start = html.find(marker)
        if start < 0:
            marker = "window[\"ytInitialData\"] = "
            start = html.find(marker)
        if start < 0:
            return None
        start += len(marker)
        end = html.find(";</script>", start)
        if end < 0:
            end = html.find(";", start)
        if end < 0:
            return None
        text = html[start:end].strip()
        try:
            return json.loads(text)
        except Exception:
            return None

    def _walk_json(self, node, text_values: list[str]):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"simpleText", "content"} and isinstance(value, str):
                    cleaned = self._clean_channel_description(value)
                    if cleaned:
                        text_values.append(cleaned)
                elif key == "runs" and isinstance(value, list):
                    text = "".join(str(item.get("text", "")) for item in value if isinstance(item, dict))
                    cleaned = self._clean_channel_description(text)
                    if cleaned:
                        text_values.append(cleaned)
                else:
                    self._walk_json(value, text_values)
        elif isinstance(node, list):
            for item in node:
                self._walk_json(item, text_values)

    def _find_about_description(self, text_values: list[str]) -> str:
        bad_markers = (
            "alle tools", "hier ein kleiner auszug", "mainboard tester", "alibaba",
            "aliexpress", "amzn.to", "letzte videobeschreibung", "playlist-link",
            "letztes importiertes video",
        )
        candidates = []
        for text in text_values:
            lowered = text.lower()
            if len(text) < 40:
                continue
            if any(marker in lowered for marker in bad_markers):
                continue
            if "auf meinem kanal" in lowered or "kanal" in lowered or "videos" in lowered:
                candidates.append(text)
        if candidates:
            candidates.sort(key=len, reverse=True)
            return candidates[0]
        return ""

    def _find_about_links(self, data) -> list[dict]:
        links = []
        seen = set()

        def walk(node):
            if isinstance(node, dict):
                url = ""
                title = ""
                if "urlEndpoint" in node and isinstance(node["urlEndpoint"], dict):
                    url = str(node["urlEndpoint"].get("url") or "")
                if "webCommandMetadata" in node and isinstance(node["webCommandMetadata"], dict):
                    url = url or str(node["webCommandMetadata"].get("url") or "")
                if "title" in node:
                    title = self._json_text(node.get("title"))
                if url.startswith("http") and url not in seen:
                    seen.add(url)
                    links.append({"title": title, "url": url})
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)
        return links[:20]

    def _find_about_banner(self, data) -> str:
        urls = []

        def walk(node):
            if isinstance(node, dict):
                if "url" in node and isinstance(node.get("url"), str):
                    url = node["url"]
                    if "yt3.googleusercontent.com" in url and ("banner" in url.lower() or "fcrop" in url.lower()):
                        urls.append(url)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)
        return urls[-1] if urls else ""

    def _find_about_stats(self, text_values: list[str]) -> dict:
        result = {}
        for text in text_values:
            lower = text.lower()
            if "abonnent" in lower and not result.get("subscriber_count"):
                result["subscriber_count"] = text
            elif "video" in lower and re.search(r"\d", text) and not result.get("video_count"):
                result["video_count"] = text
            elif "aufruf" in lower and not result.get("view_count"):
                result["view_count"] = text
            elif "beigetreten" in lower and not result.get("joined_date"):
                result["joined_date"] = text
            elif text.strip().lower() in {"deutschland", "germany", "österreich", "austria", "schweiz", "switzerland"}:
                result["country"] = text.strip()
        return result

    def _json_text(self, value) -> str:
        if isinstance(value, str):
            return self._clean_channel_description(value)
        if isinstance(value, dict):
            if isinstance(value.get("simpleText"), str):
                return self._clean_channel_description(value.get("simpleText"))
            if isinstance(value.get("runs"), list):
                return self._clean_channel_description("".join(str(item.get("text", "")) for item in value["runs"] if isinstance(item, dict)))
        return ""

    def _clean_channel_description(self, text: str) -> str:
        text = unescape(str(text or ""))
        text = text.replace("\\n", "\n")
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _looks_like_video_description(self, text: str) -> bool:
        lowered = str(text or "").lower()
        markers = (
            "letzte videobeschreibung",
            "letztes importiertes video",
            "playlist-link",
            "alle tools",
            "mainboard tester",
            "alibaba",
            "aliexpress",
            "amzn.to",
            "youtu.be/",
            "watch?v=",
        )
        return any(marker in lowered for marker in markers)

    def extract_videos(self, url: str, limit=None) -> list[dict]:
        if not url:
            return []

        text_url = str(url or "").strip()
        if "playlist" in text_url or re.fullmatch(r"[A-Za-z0-9_-]{8,}", text_url):
            normalized = self.normalize_playlist_url(text_url) if hasattr(self, "normalize_playlist_url") else text_url
            if normalized:
                text_url = normalized
            elif text_url.startswith(("PL", "UU", "OLAK", "RD", "LL")):
                return []

        info = self._extract_info_cached(text_url, limit=limit, cache_tag="videos") if hasattr(self, "_extract_info_cached") else None
        if info is None and not hasattr(self, "_extract_info_cached"):
            options = {"quiet": True, "extract_flat": True, "ignoreerrors": True, "skip_download": True}
            if limit is not None:
                options["playlistend"] = int(limit)
            try:
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(text_url, download=False)
            except Exception:
                return []

        entries = info.get("entries", []) if info else []
        videos = []
        seen = set()
        for entry in entries:
            video = self._entry_to_video(entry)
            if video is None:
                continue
            video_id = video.get("id") or video.get("video_id") or video.get("url") or ""
            if video_id and video_id in seen:
                continue
            if video_id:
                seen.add(video_id)
            videos.append(video)
        return videos

    def get_channel_videos(self, channel_url: str, limit=None) -> list[dict]:
        """Liest den normalen Videos-Reiter eines Kanals robust."""
        if not channel_url:
            return []

        return self.extract_videos(self.to_videos_url(channel_url), limit=limit)

    def _playlist_id_from_value(self, value: str) -> str:
        """Extrahiert eine echte YouTube-Playlist-ID aus URL/Text.

        Wichtig: yt-dlp liefert bei Kanal-/Tab-Einträgen manchmal gekürzte IDs
        wie "PLL_qv9KdKY". Solche Werte erzeugen bei YouTube HTTP 400 und
        dürfen nicht als Playlist-URL gespeichert oder geladen werden.
        """
        text = str(value or "").strip()
        if not text:
            return ""

        patterns = (
            r"[?&]list=([A-Za-z0-9_-]{12,})",
            r"/playlist/([A-Za-z0-9_-]{12,})",
            r"^([A-Za-z0-9_-]{12,})$",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                candidate = match.group(1)
                if self._is_valid_playlist_id(candidate):
                    return candidate
        return ""

    def _is_valid_playlist_id(self, playlist_id: str) -> bool:
        playlist_id = str(playlist_id or "").strip()
        if len(playlist_id) < 12:
            return False
        if not re.fullmatch(r"[A-Za-z0-9_-]+", playlist_id):
            return False
        # Gängige YouTube-Playlist-IDs. Alles andere lieber nicht blind laden,
        # weil falsche IDs direkt HTTP 400 auslösen.
        return playlist_id.startswith(("PL", "UU", "UULF", "UUSH", "UULV", "UUMO", "OLAK5uy_", "RD", "LL"))

    def normalize_playlist_url(self, value: str) -> str:
        playlist_id = self._playlist_id_from_value(value)
        if not playlist_id:
            return ""
        return f"https://www.youtube.com/playlist?list={playlist_id}"

    def get_playlists(self, channel_url: str) -> list[dict]:
        if not channel_url:
            return []

        playlists_url = self.to_playlists_url(channel_url)
        info = self._extract_info_cached(playlists_url, cache_tag="playlists") if hasattr(self, "_extract_info_cached") else None
        if info is None and not hasattr(self, "_extract_info_cached"):
            options = {"quiet": True, "extract_flat": True, "ignoreerrors": True, "skip_download": True}
            try:
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(playlists_url, download=False)
            except Exception:
                return []

        playlists = []
        seen_ids = set()
        entries = info.get("entries", []) if info else []
        for entry in entries:
            if not entry:
                continue

            raw_url = str(entry.get("webpage_url") or entry.get("url") or "").strip()
            raw_id = str(entry.get("id") or "").strip()
            playlist_id = self._playlist_id_from_value(raw_url) or self._playlist_id_from_value(raw_id)

            if not playlist_id or playlist_id in seen_ids:
                continue
            seen_ids.add(playlist_id)

            title = str(entry.get("title") or "").strip()
            if title.lower() in {"", "ohne titel", "untitled", "none", "null", "nan", "playlists", "playlist"}:
                title = f"Playlist {len(playlists) + 1}"

            playlist_url = self.normalize_playlist_url(playlist_id)
            if not playlist_url:
                continue

            thumbnail_url = self._best_image_url(entry.get("thumbnails", []) or [])
            playlists.append({
                "id": playlist_id,
                "title": title,
                "playlist_name": title,
                "url": playlist_url,
                "thumbnail_url": thumbnail_url,
                "thumbnail": thumbnail_url,
            })

        return playlists

    def get_playlist_video_count(self, playlist_url: str) -> int:
        if hasattr(self, "normalize_playlist_url"):
            playlist_url = self.normalize_playlist_url(playlist_url)
        if not playlist_url:
            return 0

        info = self._extract_info_cached(playlist_url, cache_tag="playlist_count") if hasattr(self, "_extract_info_cached") else None
        if info is None and not hasattr(self, "_extract_info_cached"):
            options = {"quiet": True, "extract_flat": True, "ignoreerrors": True, "skip_download": True}
            try:
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(playlist_url, download=False)
            except Exception:
                return 0
        entries = info.get("entries", []) if info else []
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
        url = str(channel_url or "").strip()
        if not url:
            return ""

        # Reine UC-Channel-ID sauber in eine Channel-URL verwandeln.
        if re.fullmatch(r"UC[A-Za-z0-9_-]{20,}", url):
            return f"https://www.youtube.com/channel/{url}/playlists"

        # Handle ohne Domain erlauben.
        if url.startswith("@"):
            return f"https://www.youtube.com/{url}/playlists"

        # Playlist-URL nicht zu /playlists umbauen.
        if "playlist?list=" in url:
            return url

        for old in ("/videos", "/featured", "/streams", "/shorts", "/community"):
            if old in url:
                return url.replace(old, "/playlists")
        if "/playlists" in url:
            return url
        return url.rstrip("/") + "/playlists"

    def to_featured_url(self, channel_url: str) -> str:
        base = self.normalize_channel_url(channel_url)
        if not base:
            return ""
        return base.rstrip("/") + "/featured"

    def _collect_playlists_from_info(self, info) -> list[dict]:
        collected = []

        def walk(node):
            if not node:
                return
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict):
                return

            playlist = self._entry_to_playlist(node)
            if playlist is not None:
                collected.append(playlist)

            entries = node.get("entries")
            if entries:
                walk(entries)

        walk(info)
        return collected

    def _entry_to_playlist(self, entry: dict | None) -> dict | None:
        if not entry:
            return None

        raw_url = str(entry.get("webpage_url") or entry.get("url") or "").strip()
        playlist_id = str(entry.get("id") or "").strip()
        title = str(entry.get("title") or entry.get("playlist_title") or "Ohne Titel").strip() or "Ohne Titel"
        entry_type = str(entry.get("_type") or entry.get("ie_key") or "").lower()

        list_match = re.search(r"(?:list=|/playlist\?list=)([A-Za-z0-9_-]+)", raw_url)
        if list_match:
            playlist_id = list_match.group(1)

        looks_like_playlist = (
            "playlist" in entry_type
            or "playlist" in raw_url
            or "list=" in raw_url
            or playlist_id.startswith(("PL", "UU", "OLAK", "RD"))
        )
        if not looks_like_playlist:
            return None

        # Uploads-/Channel-Sammellisten nicht als normale Playlist anzeigen.
        if playlist_id.startswith("UU") and "uploads" in title.lower():
            return None

        url = raw_url
        if playlist_id and not url.startswith("http"):
            url = f"https://www.youtube.com/playlist?list={playlist_id}"
        if playlist_id and "list=" not in url:
            url = f"https://www.youtube.com/playlist?list={playlist_id}"

        thumbnail_url = self._best_image_url(entry.get("thumbnails", []) or [])
        video_count = entry.get("playlist_count") or entry.get("n_entries") or entry.get("view_count") or 0

        return {
            "id": playlist_id,
            "title": title,
            "url": url,
            "thumbnail_url": thumbnail_url,
            "thumbnail": thumbnail_url,
            "video_count": int(video_count or 0) if str(video_count or "0").isdigit() else 0,
        }

    def to_videos_url(self, channel_url: str) -> str:
        base = self.normalize_channel_url(channel_url)
        if not base:
            return ""
        return base.rstrip("/") + "/videos"

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

        # Reine Playlist-/Kanal-Zeilen dürfen nie als Video in der Auswahl landen.
        if "playlist" in entry_type and "watch" not in raw_url and "youtu.be/" not in raw_url and "/shorts/" not in raw_url:
            return None
        if entry_type in {"channel", "url", "url_transparent"} and not self._extract_video_id_from_url(raw_url):
            return None

        video_id = str(entry.get("id") or "").strip()
        url_video_id = self._extract_video_id_from_url(raw_url)
        if url_video_id:
            video_id = url_video_id

        # Echte YouTube-Video-IDs haben 11 Zeichen. Playlist-/Channel-IDs wie
        # PL..., UU..., UC... sind hier Platzhalter und müssen raus.
        if video_id and not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            if not url_video_id:
                return None

        webpage_url = raw_url
        if video_id and not webpage_url.startswith("http"):
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        elif video_id and "watch" not in webpage_url and "youtu.be" not in webpage_url and "shorts" not in webpage_url:
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"

        title = self._best_title(entry)
        bad_titles = {
            "", "ohne titel", "untitled", "none", "null", "nan",
            "kanalvideo", "channel video", "playlist", "playlists",
            "videos", "uploads", "deleted video", "private video",
            "[deleted video]", "[private video]",
        }
        if title.strip().lower() in bad_titles:
            # Lieber ausblenden als wieder "Ohne Titel/Kanalvideo" anzeigen.
            # Solche Zeilen sind bei yt-dlp flat meistens Tab-/Playlist-Platzhalter.
            return None

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
