from pathlib import Path
import json
import re
import shutil
import time
import uuid
import urllib.request
import xml.etree.ElementTree as ET

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from src.mediahub.services.image_manager import ImageAssetManager

try:
    from PIL import Image
except Exception:
    Image = None


class DownloadCancelled(Exception):
    pass


class DownloadService:
    MEDIA_EXTENSIONS = {
        ".mkv", ".mp4", ".webm", ".avi", ".mov",
        ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wav"
    }

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    MODE_SEASONS_ONLY = "Nur Staffeln"
    MODE_PLAYLIST_SEASONS = "Playlist → Staffel"
    MODE_PLAYLIST_ONLY = "Playlist ohne Staffel"
    MODE_SEASON_IS_PLAYLIST = "Staffel = Playlist"

    def __init__(self, tool_service=None):
        self.tool_service = tool_service
        self.last_download_status = ""
        self.last_download_error = ""
        self.last_downloaded_files = []
        self.image_manager = ImageAssetManager(Path.cwd())

    @staticmethod
    def is_members_only_error_text(text: str) -> bool:
        lower = str(text or "").lower()
        markers = (
            "members-only",
            "members only",
            "member-only",
            "channel's members",
            "channel members",
            "join this channel",
            "kanalmitglied",
            "kanalmitgliedschaft",
            "kanal-abonnenten",
            "abo-video",
            "subscriber-only",
            "subscribers only",
            "premium_only",
            "premium only",
            "requires payment",
            "zur kanal unterstützung",
            "zur kanal unterstuetzung",
        )
        return any(marker in lower for marker in markers)


    def _precheck_video_availability(self, url: str, log_callback=None):
        """Prüft vor dem eigentlichen Download, ob yt-dlp bereits meldet,
        dass das Video nur für Kanalmitglieder verfügbar ist.

        Wichtig: Manche Mitglieder-Videos lösen beim normalen Download keinen
        Python-DownloadError aus, sondern landen nur im yt-dlp-Fehlertext. Diese
        Vorprüfung macht den Spezialfall zuverlässiger erkennbar.
        """
        if not url:
            return "ok"

        options = {
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": False,
            "noplaylist": True,
        }

        if self.tool_service:
            deno_path = getattr(self.tool_service, "deno_path", lambda: None)()
            if deno_path:
                options["js_runtimes"] = {"deno": {"path": deno_path}}

        try:
            with YoutubeDL(options) as ydl:
                ydl.extract_info(url, download=False)
        except DownloadError as error:
            raw = str(error)
            self.last_download_error = raw
            if self.is_members_only_error_text(raw):
                self.last_download_status = "members_only"
                if log_callback:
                    log_callback("🔒 Mitglieder-Video bereits vor dem Download erkannt.")
                    log_callback(self.format_download_error(error))
                return "members_only"
            return "unknown_error"
        except Exception as error:
            raw = str(error)
            self.last_download_error = raw
            if self.is_members_only_error_text(raw):
                self.last_download_status = "members_only"
                if log_callback:
                    log_callback("🔒 Mitglieder-Video bereits vor dem Download erkannt.")
                    log_callback(self.format_download_error(error))
                return "members_only"
            return "unknown_error"

        return "ok"


    def download_latest_video(self, channel, log_callback=None, progress_callback=None, cancel_callback=None):
        self.last_download_status = ""
        self.last_download_error = ""
        self.last_downloaded_files = []

        base_work_dir = Path(channel.work_folder or "downloads/work") / channel.name
        base_work_dir.mkdir(parents=True, exist_ok=True)
        self.cleanup_empty_active_dirs(base_work_dir)

        # Mit Plex-Ziel arbeiten wir in einem temporären Ordner und importieren danach.
        # Ohne Zielordner schreiben wir direkt in den Arbeitsordner. So entstehen keine
        # zusätzlichen Unterordner und fertige Downloads bleiben dort, wo der Nutzer sie erwartet.
        work_dir = self.create_download_work_dir(base_work_dir) if channel.target_folder else base_work_dir
        archive_file = base_work_dir / "archive.txt"
        download_started_at = time.time()

        resolution_map = {
            "Beste": "bv*+ba/b",
            "4K": "bv*[height<=2160]+ba/b[height<=2160]",
            "1440p": "bv*[height<=1440]+ba/b[height<=1440]",
            "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
            "720p": "bv*[height<=720]+ba/b[height<=720]",
            "480p": "bv*[height<=480]+ba/b[height<=480]",
        }

        container = channel.container.lower()
        fmt = resolution_map.get(channel.resolution, "bv*[height<=1080]+ba/b[height<=1080]")

        postprocessors = []

        if channel.audio_only:
            fmt = "bestaudio/best"
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": channel.audio_format.lower(),
                "preferredquality": "320",
            })

        def hook(data):
            if cancel_callback and cancel_callback():
                raise DownloadCancelled("Download wurde abgebrochen.")

            status = data.get("status")

            if status == "downloading":
                percent_value = self._extract_percent(data)

                if progress_callback:
                    progress_callback(percent_value)

                if log_callback:
                    percent = data.get("_percent_str", "").strip()
                    speed = data.get("_speed_str", "").strip()
                    eta = data.get("_eta_str", "").strip()
                    log_callback(f"Download läuft: {percent} | {speed} | Rest: {eta}")

            elif status == "finished":
                if progress_callback:
                    progress_callback(100)

                if log_callback:
                    log_callback("Download fertig, Datei wird verarbeitet...")

        options = {
            "format": fmt,
            "outtmpl": str(work_dir / "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s"),
            "download_archive": str(archive_file),
            "ignoreerrors": True,
            "playlistend": 1,
            "progress_hooks": [hook],
            "writethumbnail": True,
            "writeinfojson": True,
            "quiet": True,
            "noprogress": True,
            "postprocessors": postprocessors,
        }

        if not channel.audio_only:
            options["merge_output_format"] = container

        if self.tool_service:
            options["ffmpeg_location"] = self.tool_service.ffmpeg_location()

            deno_path = getattr(self.tool_service, "deno_path", lambda: None)()
            if deno_path:
                options["js_runtimes"] = {"deno": {"path": deno_path}}

        if log_callback:
            log_callback(f"Download startet: {channel.name}")
            log_callback(f"Dateinamenschema: {channel.filename_template}")
            log_callback(f"Arbeitsordner: {base_work_dir}")
            log_callback(f"Temporärer Downloadordner: {work_dir}")
            log_callback(f"Plex-Ziel: {channel.target_folder or 'nicht gesetzt'}")

            playlist_name = getattr(channel, "playlist_name", "")
            playlist_mode = getattr(channel, "playlist_folder_mode", self.MODE_SEASONS_ONLY)
            playlist_season = getattr(channel, "playlist_season", 1)

            if playlist_name:
                log_callback(f"Playlist: {playlist_name}")

            log_callback(f"Ablage-Modus: {playlist_mode}")
            log_callback(f"Staffel: {playlist_season}")

        if progress_callback:
            progress_callback(0)

        availability = self._precheck_video_availability(channel.url, log_callback)
        if availability == "members_only":
            return "members_only"

        try:
            with YoutubeDL(options) as ydl:
                ydl.download([channel.url])
        except DownloadCancelled:
            if log_callback:
                log_callback("Download wurde abgebrochen.")
            return False
        except DownloadError as error:
            raw_message = str(error)
            message = self.format_download_error(error)
            self.last_download_error = raw_message

            if self.is_members_only_error_text(raw_message) or self.is_members_only_error_text(message):
                self.last_download_status = "members_only"
                if log_callback:
                    log_callback("🔒 Mitglieder-Video erkannt. Download wird übersprungen.")
                    log_callback(message)
                return "members_only"

            self.last_download_status = "error"
            if log_callback:
                log_callback(message)
            return False

        if progress_callback:
            progress_callback(100)

        try:
            if channel.target_folder:
                final_files = self.import_to_plex(
                    channel,
                    work_dir,
                    log_callback,
                    since=download_started_at - 2,
                )
            else:
                if log_callback:
                    log_callback("Kein Plex-Ziel gesetzt. Dateien bleiben direkt im Arbeitsordner.")
                self.create_work_nfo_files(
                    channel,
                    work_dir,
                    log_callback,
                    since=download_started_at - 2,
                )
                final_files = self.find_media_files(work_dir)
                final_files = [
                    path for path in final_files
                    if path.stat().st_mtime >= download_started_at - 2
                ]

            self.last_downloaded_files = [
                str(Path(path).resolve())
                for path in (final_files or [])
                if Path(path).is_file()
            ]
        except Exception as error:
            if log_callback:
                log_callback(f"Import-/NFO-Fehler: {type(error).__name__}: {error}")
                log_callback("Download-Dateien bleiben im Arbeitsordner erhalten.")
            return False

        if channel.target_folder:
            self.remove_empty_temp_dir(work_dir)

        if not self.last_downloaded_files:
            if log_callback:
                log_callback("Download abgeschlossen, aber die endgültige Mediendatei wurde nicht gefunden.")
            self.last_download_status = "file_not_found"
            return False

        if log_callback:
            log_callback(f"Lokale Datei: {self.last_downloaded_files[0]}")
            log_callback("Download abgeschlossen.")

        return True

    def cleanup_empty_active_dirs(self, base_work_dir: Path):
        active_root = base_work_dir / "_active"
        if not active_root.exists():
            return

        for path in sorted(active_root.glob("download_*")):
            if path.is_dir():
                self.remove_empty_temp_dir(path)

        self.remove_empty_temp_dir(active_root)

    def create_download_work_dir(self, base_work_dir: Path) -> Path:
        temp_root = base_work_dir / "_active"
        temp_root.mkdir(parents=True, exist_ok=True)
        name = f"download_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        work_dir = temp_root / name
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    def move_completed_work_files(self, source_dir: Path, target_dir: Path, log_callback=None):
        target_dir.mkdir(parents=True, exist_ok=True)

        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue

            if path.suffix.lower() in {".part", ".ytdl"} or path.name.endswith(".part"):
                if log_callback:
                    log_callback(f"Unfertige Datei bleibt im temporären Ordner: {path.name}")
                continue

            relative = path.relative_to(source_dir)
            destination = target_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination = self.unique_destination(destination)
            shutil.move(str(path), str(destination))

        self.remove_empty_temp_dir(source_dir)

    def unique_destination(self, destination: Path) -> Path:
        if not destination.exists():
            return destination

        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent

        counter = 2
        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def remove_empty_temp_dir(self, work_dir: Path):
        try:
            for path in sorted(work_dir.rglob("*"), reverse=True):
                if path.is_dir():
                    path.rmdir()
            work_dir.rmdir()
        except OSError:
            pass


    def format_download_error(self, error) -> str:
        message = str(error)
        lower = message.lower()

        if self.is_members_only_error_text(lower):
            return "Video nicht verfügbar: nur für Kanal-Abonnenten/Mitglieder."

        if "private video" in lower:
            return "Video nicht verfügbar: privat."

        if "unavailable" in lower:
            return "Video nicht verfügbar."

        return f"Download-Fehler: {message}"

    def import_to_plex(self, channel, work_dir: Path, log_callback=None, since: float | None = None):
        media_files = self.find_media_files(work_dir)

        if since is not None:
            media_files = [path for path in media_files if path.stat().st_mtime >= since]

        if not media_files:
            if log_callback:
                log_callback("Keine Mediendatei zum Importieren gefunden.")
            return []

        series_dir = Path(channel.target_folder) / channel.name
        series_dir.mkdir(parents=True, exist_ok=True)

        first_media_info = self.find_info_for_media(media_files[0]) if media_files else {}

        if getattr(channel, "create_nfo", True):
            self.create_tvshow_nfo(channel, series_dir, first_media_info)

        mode = self.get_playlist_mode(channel)
        playlist_name = self.clean_filename(getattr(channel, "playlist_name", ""))
        playlist_season = self.get_playlist_season(channel)

        if log_callback:
            log_callback(f"Plex-Import-Modus: {mode}")
            if playlist_name:
                log_callback(f"Plex-Playlist-Name: {playlist_name}")
            log_callback(f"Plex-Staffel: {playlist_season}")

        # Serienbild: Kanalposter/Logo.
        self.create_plex_series_images(channel, series_dir, log_callback)

        # Staffelbild: Playlist-Thumbnail. Wird einmal pro Import vorbereitet.
        playlist_image = self.find_or_download_playlist_image(channel, work_dir, log_callback)
        imported_files = []

        for media_file in media_files:
            info = self.find_info_for_media(media_file)
            title = self.get_title(media_file, info)
            clean_title = self.clean_filename(title)

            # Folgenbild: Video-Thumbnail direkt neben der Videodatei.
            episode_image = self.find_best_image_for_media(media_file, info)

            target_dir, season_number = self.get_target_dir_and_season(
                channel=channel,
                series_dir=series_dir,
                mode=mode,
                playlist_name=playlist_name,
                playlist_season=playlist_season,
            )

            target_dir.mkdir(parents=True, exist_ok=True)

            # Staffel-/Playlistbild: echtes Playlistbild oder gar kein Staffelposter.
            self.create_plex_season_images(
                channel=channel,
                target_dir=target_dir,
                playlist_image=playlist_image,
                season=season_number,
                log_callback=log_callback,
            )

            if getattr(channel, "create_nfo", True):
                self.create_season_nfo(
                    season_dir=target_dir,
                    channel=channel,
                    season=season_number,
                    playlist_name=playlist_name,
                )

            episode_number = self.next_episode_number(target_dir, season_number)

            base_name = self.build_filename(
                channel=channel,
                title=clean_title,
                season=season_number,
                episode=episode_number,
                info=info,
            )

            new_media = target_dir / f"{base_name}{media_file.suffix.lower()}"
            self.move_file(media_file, new_media)
            imported_files.append(new_media)

            if getattr(channel, "create_nfo", True):
                self.create_episode_nfo(
                    nfo_path=target_dir / f"{base_name}.nfo",
                    channel=channel,
                    info=info,
                    title=title,
                    season=season_number,
                    episode=episode_number,
                )

            self.move_sidecars(media_file, target_dir, base_name, info)

            if log_callback:
                log_callback(f"Importiert: {new_media}")

        if channel.clean_work_folder:
            self.clean_work_dir(work_dir, log_callback)

        return imported_files

    def create_work_nfo_files(self, channel, work_dir: Path, log_callback=None, since: float | None = None):
        if not getattr(channel, "create_nfo", True):
            return

        media_files = self.find_media_files(work_dir)

        if since is not None:
            media_files = [path for path in media_files if path.stat().st_mtime >= since]

        if not media_files:
            if log_callback:
                log_callback("Keine neue Mediendatei für NFO gefunden.")
            return

        for index, media_file in enumerate(media_files, start=1):
            nfo_path = media_file.with_suffix(".nfo")

            if nfo_path.exists():
                continue

            info = self.find_info_for_media(media_file)
            title = self.get_title(media_file, info)
            season = self.get_playlist_season(channel)
            episode = index

            self.create_episode_nfo(
                nfo_path=nfo_path,
                channel=channel,
                info=info,
                title=title,
                season=season,
                episode=episode,
            )

            if log_callback:
                log_callback(f"NFO erzeugt: {nfo_path.name}")

    def get_playlist_mode(self, channel) -> str:
        mode = getattr(channel, "playlist_folder_mode", self.MODE_SEASONS_ONLY)

        valid_modes = {
            self.MODE_SEASONS_ONLY,
            self.MODE_PLAYLIST_SEASONS,
            self.MODE_PLAYLIST_ONLY,
            self.MODE_SEASON_IS_PLAYLIST,
            "Playlist-Ordner + Staffeln",
        }

        if mode not in valid_modes:
            return self.MODE_SEASONS_ONLY

        if mode == "Playlist-Ordner + Staffeln":
            return self.MODE_PLAYLIST_SEASONS

        return mode

    def get_playlist_season(self, channel) -> int:
        try:
            season = int(getattr(channel, "playlist_season", 1))
        except Exception:
            season = 1

        if season < 0:
            season = 0

        return season

    def get_target_dir_and_season(
        self,
        channel,
        series_dir: Path,
        mode: str,
        playlist_name: str,
        playlist_season: int,
    ):
        if mode == self.MODE_PLAYLIST_SEASONS and playlist_name:
            return series_dir / playlist_name / f"Season {playlist_season:02}", playlist_season

        if mode == self.MODE_PLAYLIST_ONLY and playlist_name:
            return series_dir / playlist_name, playlist_season

        if mode == self.MODE_SEASON_IS_PLAYLIST and playlist_name:
            season_dir = series_dir / f"Season {playlist_season:02} - {playlist_name}"
            return season_dir, playlist_season

        return series_dir / f"Season {playlist_season:02}", playlist_season

    def build_filename(self, channel, title: str, season: int, episode: int, info: dict) -> str:
        template = channel.filename_template or "{title} S{season:02}E{episode:02}"
        year = self.extract_year(info)

        try:
            name = template.format(
                title=title,
                series=channel.name,
                year=year,
                season=season,
                episode=episode,
            )
        except Exception:
            name = f"{title} S{season:02}E{episode:02}"

        return self.clean_filename(name)

    def extract_year(self, info: dict) -> str:
        upload_date = info.get("upload_date", "")

        if len(upload_date) >= 4:
            return upload_date[:4]

        release_year = info.get("release_year")
        if release_year:
            return str(release_year)

        return ""

    def find_media_files(self, work_dir: Path) -> list[Path]:
        files = []

        for path in work_dir.rglob("*"):
            if not path.is_file():
                continue

            if path.name.lower() == "archive.txt":
                continue

            if path.suffix.lower() in self.MEDIA_EXTENSIONS:
                files.append(path)

        return sorted(files, key=lambda p: p.stat().st_mtime)

    def find_info_for_media(self, media_file: Path) -> dict:
        same_stem_json = media_file.with_suffix(".info.json")

        if same_stem_json.exists():
            return self.load_json(same_stem_json)

        candidates = []

        for json_file in media_file.parent.glob("*.info.json"):
            data = self.load_json(json_file)

            if data.get("_type") in {"playlist", "multi_video"}:
                continue

            candidates.append((json_file.stat().st_mtime, data))

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]

        return {}

    def move_sidecars(self, media_file: Path, target_dir: Path, base_name: str, info: dict):
        source_stem = media_file.stem

        for path in list(media_file.parent.iterdir()):
            if not path.is_file():
                continue

            if path.name.lower() == "archive.txt":
                continue

            if path == media_file:
                continue

            lower_name = path.name.lower()

            if lower_name.endswith(".info.json"):
                data = self.load_json(path)
                if data.get("_type") in {"playlist", "multi_video"}:
                    continue

                destination = target_dir / f"{base_name}.info.json"
                self.move_file(path, destination)
                continue

            if path.suffix.lower() in self.IMAGE_EXTENSIONS:
                if path.stem.startswith(source_stem) or source_stem.startswith(path.stem):
                    # Folgenbild immer als JPG im Zielordner.
                    destination = target_dir / f"{base_name}.jpg"
                    if self.copy_or_convert_image_to_jpg(path, destination, "episode"):
                        path.unlink(missing_ok=True)
                    else:
                        # Fallback: nichts verlieren.
                        fallback = target_dir / f"{base_name}{path.suffix.lower()}"
                        self.move_file(path, fallback)

    def create_plex_series_images(self, channel, series_dir: Path, log_callback=None):
        """Legt Serienbilder für Plex an.

        Serie = Kanal.
        Deshalb wird hier zuerst das gespeicherte Kanalposter/Kanallogo verwendet.
        Ergebnis:
            poster.jpg
            fanart.jpg
        """
        if getattr(channel, "create_poster", True):
            poster = self._existing_path(getattr(channel, "poster", ""))
            if poster:
                destination = series_dir / "poster.jpg"
                if self.copy_or_convert_image_to_jpg(poster, destination, "poster"):
                    if log_callback:
                        log_callback(f"Serienposter/Kanallogo erzeugt: {destination.name}")
            elif log_callback:
                log_callback("Kein Kanalposter/Kanallogo für Serienposter gefunden.")

        if getattr(channel, "create_fanart", True):
            fanart = self._existing_path(getattr(channel, "fanart", ""))
            if fanart:
                destination = series_dir / "fanart.jpg"
                if self.copy_or_convert_image_to_jpg(fanart, destination, "fanart"):
                    if log_callback:
                        log_callback(f"Serien-Fanart erzeugt: {destination.name}")

    def create_plex_season_images(
        self,
        channel,
        target_dir: Path,
        playlist_image: Path | None = None,
        season: int = 1,
        log_callback=None,
    ):
        """Legt Staffel-/Playlistposter für Plex an.

        Plex erkennt Staffelposter zuverlässig mit:
            Season 01/Season01.jpg

        Zusätzlich erzeugen wir weiter:
            Season 01/poster.jpg

        Das hilft anderen Tools und schadet Plex nicht.
        """
        if not getattr(channel, "create_poster", True):
            return

        source = playlist_image
        if not source or not self._valid_playlist_image_for_channel(channel, source):
            if log_callback:
                log_callback("Kein gültiges Playlistbild für Staffel-/Playlistposter gefunden. Es wird kein falsches Ersatzbild verwendet.")
            return

        destinations = [
            target_dir / "poster.jpg",
            target_dir / f"Season{int(season):02}.jpg",
        ]

        created = []
        for destination in destinations:
            if destination.exists():
                continue

            # Playlist-/Staffelposter bewusst immer neu schreiben: alte falsche
            # Poster mit eingebranntem schwarzem Rand sollen beim nächsten Import
            # ersetzt werden.
            if self.copy_or_convert_image_to_jpg(source, destination, "playlist_poster"):
                created.append(destination.name)

        if created and log_callback:
            log_callback(f"Staffel-/Playlistposter erzeugt: {', '.join(created)}")

    def find_or_download_playlist_image(self, channel, work_dir: Path, log_callback=None):
        """Liefert ausschließlich ein lokal gespeichertes Playlistbild.

        Der Plex-Import soll keine Bilder mehr im Internet suchen und keine
        falschen Fallbacks verwenden. Playlistbilder werden beim Einlesen im
        Assistenten/Playlist-Service unter assets/channels/... gespeichert.
        """
        saved = self._existing_path(getattr(channel, "playlist_image", ""))
        if saved and self._valid_playlist_image_for_channel(channel, saved):
            if log_callback:
                log_callback("Playlistbild aus lokalen Kanal-Einstellungen verwendet.")
            return saved

        if saved and log_callback:
            log_callback("Playlistbild verworfen: identisch/ähnlich mit Kanalbild oder Banner.")

        if log_callback:
            log_callback("Kein lokales Playlistbild gesetzt.")
        return None

    def find_local_playlist_image(self, work_dir: Path):
        names = (
            "playlist",
            "playlist_poster",
            "playlist-thumbnail",
            "playlist_thumbnail",
            "season",
            "staffel",
        )

        candidates = []
        for path in work_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in self.IMAGE_EXTENSIONS:
                continue

            lower = path.stem.lower()
            if any(name in lower for name in names):
                try:
                    candidates.append((path.stat().st_size, path))
                except OSError:
                    candidates.append((0, path))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0][1]

    def playlist_url_from_channel(self, channel) -> str:
        url = str(getattr(channel, "playlist_original", "") or "").strip()
        if url.startswith("http"):
            return url

        url = str(getattr(channel, "playlist_url", "") or "").strip()
        if url.startswith("http"):
            return url

        playlist_id = str(getattr(channel, "playlist_id", "") or "").strip()
        if playlist_id:
            return f"https://www.youtube.com/playlist?list={playlist_id}"

        return ""

    def best_thumbnail_url(self, info: dict) -> str:
        thumbnails = info.get("thumbnails", []) or []
        if thumbnails:
            for thumb in reversed(thumbnails):
                url = thumb.get("url", "")
                if url:
                    return url

        for key in ("thumbnail", "thumbnail_url"):
            url = info.get(key, "")
            if url:
                return url

        return ""

    def download_image(self, url: str, destination_without_suffix: Path):
        if not url:
            return None

        suffix = ".jpg"
        lower_url = url.lower()
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            if ext in lower_url:
                suffix = ext
                break

        destination = destination_without_suffix.with_suffix(suffix)

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "MediaHub/1.0"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read()

            if not data:
                return None

            destination.write_bytes(data)
            return destination if destination.exists() else None
        except Exception:
            return None

    def find_best_image_for_media(self, media_file: Path, info: dict | None = None):
        """Findet das Folgen-Thumbnail für das konkrete Video."""
        info = info or {}
        parent = media_file.parent
        source_stem = media_file.stem

        candidates = []

        for path in parent.iterdir():
            if not path.is_file():
                continue

            if path.suffix.lower() not in self.IMAGE_EXTENSIONS:
                continue

            score = 0
            if path.stem == source_stem:
                score = 100
            elif path.stem.startswith(source_stem) or source_stem.startswith(path.stem):
                score = 90
            elif "thumbnail" in path.name.lower() or "poster" in path.name.lower():
                score = 50
            else:
                score = 10

            try:
                size = path.stat().st_size
            except OSError:
                size = 0

            candidates.append((score, size, path))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0][2]

    def _existing_path(self, value):
        text = str(value or "").strip()
        if not text:
            return None

        path = Path(text)
        if path.exists() and path.is_file():
            return path

        return None

    def copy_or_convert_image_to_jpg(self, source: Path, destination: Path, kind: str = "poster") -> bool:
        """Kopiert oder konvertiert ein Bild nach JPG.

        Zielgrößen:
        - Poster / Staffelposter: 1000 x 1500
        - Fanart: 1920 x 1080
        - Folgenbild: 1280 x 720
        """
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)

            if Image is None:
                if source.suffix.lower() in {".jpg", ".jpeg"}:
                    shutil.copy2(str(source), str(destination))
                    return destination.exists()
                return False

            kind = (kind or "poster").lower()
            if kind == "fanart":
                target_size = (1920, 1080)
            elif kind in {"episode", "thumb", "thumbnail"}:
                target_size = (1280, 720)
            else:
                target_size = (1000, 1500)

            with Image.open(source) as image:
                image = image.convert("RGB")
                if kind in {"playlist", "playlist_poster", "season", "season_poster"}:
                    output = self.fit_playlist_poster_full_width(image, target_size)
                else:
                    output = self.fit_image_for_plex(image, target_size)
                output.save(destination, "JPEG", quality=94, optimize=True)

            return destination.exists()
        except Exception:
            return False

    def crop_dark_border(self, image, threshold: int = 18):
        """Schneidet eingebrannte schwarze Außenränder ab.

        Das ist wichtig, falls durch einen alten Fix bereits ein falsches
        SeasonXX.jpg/Posterbild mit riesigem schwarzem Rand als Quelle in
        assets/channels oder im Zielordner gelandet ist.
        """
        if Image is None:
            return image

        try:
            gray = image.convert("L")
            mask = gray.point(lambda value: 255 if value > threshold else 0)
            bbox = mask.getbbox()
            if not bbox:
                return image

            left, top, right, bottom = bbox
            width, height = image.size

            # Nur wirklich große Außenränder entfernen. Kleine dunkle Bereiche
            # im eigentlichen Thumbnail bleiben erhalten.
            if left <= 3 and top <= 3 and right >= width - 3 and bottom >= height - 3:
                return image

            cropped_w = right - left
            cropped_h = bottom - top
            # Auch sehr breite YouTube-Thumbnails können auf einem 1000x1500
            # Poster nur etwa 260-560 px hoch sein. Deshalb darf die
            # Mindesthöhe hier nicht zu groß sein.
            if cropped_w < width * 0.05 or cropped_h < height * 0.05:
                return image

            return image.crop(bbox)
        except Exception:
            return image

    def fit_playlist_poster_full_width(self, image, target_size: tuple[int, int] = (1000, 1500)):
        """Erzeugt Playlist-/Staffelposter ohne Mini-Bild in der Mitte.

        Ziel:
        - Plex-Posterfläche 1000x1500
        - Thumbnail so groß wie möglich
        - bei normalen YouTube-16:9-Bildern volle Breite
        - keine Verzerrung
        - kein links/rechts Abschneiden
        - kein unscharfer Hintergrund und kein zweites Miniaturbild
        """
        if Image is None:
            return image

        target_w, target_h = target_size
        image = self.crop_dark_border(image)
        source_w, source_h = image.size

        if source_w <= 0 or source_h <= 0:
            return Image.new("RGB", target_size, (0, 0, 0))

        # Für YouTube-Playlistbilder: zuerst auf volle Breite skalieren.
        scale = target_w / source_w
        new_w = target_w
        new_h = max(1, int(round(source_h * scale)))

        # Falls ein ungewöhnlich hohes Bild dadurch über die Posterhöhe laufen
        # würde, auf die Höhe einpassen, damit nichts abgeschnitten wird.
        if new_h > target_h:
            scale = target_h / source_h
            new_w = max(1, int(round(source_w * scale)))
            new_h = target_h

        resized = image.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGB", target_size, (0, 0, 0))
        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2
        canvas.paste(resized, (x, y))
        return canvas

    def fit_image_for_plex(self, image, target_size: tuple[int, int]):
        """Erzeugt ein Plex-taugliches Bild ohne harten Beschnitt."""
        if Image is None:
            return image

        try:
            from PIL import ImageFilter
        except Exception:
            ImageFilter = None

        target_w, target_h = target_size
        source_w, source_h = image.size

        if source_w <= 0 or source_h <= 0:
            return Image.new("RGB", target_size, (0, 0, 0))

        bg_scale = max(target_w / source_w, target_h / source_h)
        bg_size = (max(1, int(source_w * bg_scale)), max(1, int(source_h * bg_scale)))
        background = image.resize(bg_size, Image.LANCZOS)

        left = max(0, (background.width - target_w) // 2)
        top = max(0, (background.height - target_h) // 2)
        background = background.crop((left, top, left + target_w, top + target_h))

        if ImageFilter is not None:
            background = background.filter(ImageFilter.GaussianBlur(radius=18))

        overlay = Image.new("RGB", target_size, (0, 0, 0))
        background = Image.blend(background, overlay, 0.25)

        fg_scale = min(target_w / source_w, target_h / source_h)
        fg_size = (max(1, int(source_w * fg_scale)), max(1, int(source_h * fg_scale)))
        foreground = image.resize(fg_size, Image.LANCZOS)

        x = (target_w - foreground.width) // 2
        y = (target_h - foreground.height) // 2
        background.paste(foreground, (x, y))

        return background


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

    def _valid_playlist_image_for_channel(self, channel, path: Path) -> bool:
        """Prüft, ob ein Playlistbild wirklich als Staffelposter verwendet werden darf.

        Wichtig:
        - Staffelposter darf nicht fehlen.
        - Staffelposter darf nicht identisch/ähnlich mit Kanalposter oder Banner sein.
        """
        path = self._existing_path(str(path or ""))
        if not path:
            return False

        for other in (
            self._existing_path(getattr(channel, "poster", "")),
            self._existing_path(getattr(channel, "fanart", "")),
        ):
            if other and self._images_look_same(path, other):
                return False

        return True


    def create_tvshow_nfo(self, channel, series_dir: Path, info: dict | None = None):
        """Schreibt/aktualisiert tvshow.nfo für die Plex-Serie.

        Serie = YouTube-Kanal. Hier werden bewusst nur echte Kanalinfos
        geschrieben: Kanalname, Kanalbeschreibung und einfache Kanal-Daten.
        Keine letzte Videobeschreibung und keine aktuellen Playlist-/Video-Details.
        """
        info = info or {}
        nfo_path = series_dir / "tvshow.nfo"

        def first_text(*values):
            for value in values:
                text_value = str(value or "").strip()
                if text_value:
                    return text_value
            return ""

        def first_number(*values):
            for value in values:
                if value is None:
                    continue
                text_value = str(value).strip()
                if not text_value:
                    continue
                try:
                    number = int(float(text_value))
                    return str(number)
                except Exception:
                    return text_value
            return ""

        def add(parent, tag, value):
            value = str(value or "").strip()
            if not value:
                return None
            node = ET.SubElement(parent, tag)
            node.text = value
            return node

        def add_uniqueid(parent, value, id_type="youtube", default=False):
            value = str(value or "").strip()
            if not value:
                return None
            node = ET.SubElement(parent, "uniqueid")
            node.set("type", id_type)
            if default:
                node.set("default", "true")
            node.text = value
            return node

        channel_name = first_text(
            getattr(channel, "name", ""),
            getattr(channel, "youtube_name", ""),
            info.get("channel"),
            info.get("uploader"),
            info.get("channel_title"),
            "YouTube-Kanal",
        )
        youtube_name = first_text(
            getattr(channel, "youtube_name", ""),
            getattr(channel, "youtube_title", ""),
            getattr(channel, "channel_title", ""),
            info.get("channel"),
            info.get("uploader"),
            channel_name,
        )
        channel_url = first_text(
            getattr(channel, "original_channel_url", ""),
            getattr(channel, "channel_url", ""),
            getattr(channel, "source_url", ""),
            info.get("channel_url"),
            info.get("uploader_url"),
            getattr(channel, "url", ""),
        )
        channel_id = first_text(
            getattr(channel, "channel_id", ""),
            getattr(channel, "youtube_channel_id", ""),
            info.get("channel_id"),
            info.get("uploader_id"),
        )

        # Wichtig: hier absichtlich KEINE info["description"] verwenden.
        # Das ist bei yt-dlp fast immer die letzte Videobeschreibung.
        description = first_text(
            getattr(channel, "description", ""),
            getattr(channel, "channel_description", ""),
            getattr(channel, "about", ""),
            getattr(channel, "plot", ""),
        )

        if not description:
            description = f"YouTube-Kanal: {youtube_name}"
            if channel_url:
                description += f"\n\nQuelle: {channel_url}"

        subscriber_count = first_number(
            getattr(channel, "subscriber_count", ""),
            getattr(channel, "subscribers", ""),
            info.get("channel_follower_count"),
            info.get("subscriber_count"),
        )
        video_count = first_number(
            getattr(channel, "video_count", ""),
            getattr(channel, "videos_count", ""),
            info.get("channel_video_count"),
        )
        country = first_text(
            getattr(channel, "country", ""),
            getattr(channel, "channel_country", ""),
            info.get("channel_country"),
        )

        details = []
        if subscriber_count:
            details.append(f"Abonnenten: {subscriber_count}")
        if video_count:
            details.append(f"Videos: {video_count}")
        if country:
            details.append(f"Land: {country}")
        if channel_url:
            details.append(f"YouTube-Kanal: {channel_url}")
        if channel_id:
            details.append(f"Kanal-ID: {channel_id}")

        full_plot = description
        if details:
            full_plot = full_plot.rstrip() + "\n\n" + "\n".join(details)

        tvshow = ET.Element("tvshow")
        add(tvshow, "title", channel_name)
        add(tvshow, "originaltitle", youtube_name)
        add(tvshow, "sorttitle", channel_name)
        add(tvshow, "showtitle", channel_name)
        add(tvshow, "plot", full_plot)
        add(tvshow, "outline", description[:250])
        add(tvshow, "tagline", f"YouTube-Kanal: {youtube_name}")
        add(tvshow, "studio", youtube_name)
        add(tvshow, "genre", "YouTube")
        add(tvshow, "tag", "YouTube")
        add(tvshow, "tag", youtube_name)
        add(tvshow, "status", "Continuing")
        add(tvshow, "thumb", "poster.jpg")
        if (series_dir / "fanart.jpg").exists():
            add(tvshow, "fanart", "fanart.jpg")
        if channel_url:
            add(tvshow, "homepage", channel_url)
            add_uniqueid(tvshow, channel_url, "youtube", default=True)
        if channel_id:
            add_uniqueid(tvshow, channel_id, "youtube-channel-id")

        self.write_xml(nfo_path, tvshow)

    def create_season_nfo(self, season_dir: Path, channel, season: int, playlist_name: str = ""):
        """Schreibt season.nfo in den Staffel-/Playlistordner."""
        nfo_path = season_dir / "season.nfo"

        if nfo_path.exists():
            return

        season_details = ET.Element("season")

        title = playlist_name or f"Season {int(season):02}"
        plot = (
            f"YouTube-Playlist: {playlist_name}"
            if playlist_name
            else f"YouTube-Staffel {int(season):02} von {channel.name}"
        )

        ET.SubElement(season_details, "title").text = title
        ET.SubElement(season_details, "showtitle").text = channel.name
        ET.SubElement(season_details, "seasonnumber").text = str(int(season))
        ET.SubElement(season_details, "season").text = str(int(season))
        ET.SubElement(season_details, "plot").text = plot
        ET.SubElement(season_details, "outline").text = plot
        ET.SubElement(season_details, "studio").text = "YouTube"
        ET.SubElement(season_details, "genre").text = "YouTube"
        ET.SubElement(season_details, "thumb").text = f"Season{int(season):02}.jpg"

        self.write_xml(nfo_path, season_details)


    def create_episode_nfo(self, nfo_path: Path, channel, info: dict, title: str, season: int, episode: int):
        episode_details = ET.Element("episodedetails")

        ET.SubElement(episode_details, "title").text = title
        ET.SubElement(episode_details, "showtitle").text = channel.name
        ET.SubElement(episode_details, "season").text = str(season)
        ET.SubElement(episode_details, "episode").text = str(episode)
        ET.SubElement(episode_details, "studio").text = "YouTube"

        description = info.get("description") or "Keine Beschreibung vorhanden."
        ET.SubElement(episode_details, "plot").text = description
        ET.SubElement(episode_details, "outline").text = description[:250]

        duration = info.get("duration")
        if duration:
            try:
                ET.SubElement(episode_details, "runtime").text = str(int(int(duration) / 60))
            except Exception:
                pass

        upload_date = info.get("upload_date", "")
        if len(upload_date) == 8:
            aired = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            ET.SubElement(episode_details, "aired").text = aired

        webpage_url = info.get("webpage_url") or info.get("original_url") or ""
        if webpage_url:
            uniqueid = ET.SubElement(episode_details, "uniqueid")
            uniqueid.set("type", "youtube")
            uniqueid.set("default", "true")
            uniqueid.text = webpage_url
            ET.SubElement(episode_details, "homepage").text = webpage_url

        self.write_xml(nfo_path, episode_details)

    def next_episode_number(self, target_dir: Path, season: int) -> int:
        highest = 0
        pattern = re.compile(rf"S{season:02}E(\d+)", re.IGNORECASE)

        for path in target_dir.iterdir() if target_dir.exists() else []:
            match = pattern.search(path.name)
            if match:
                highest = max(highest, int(match.group(1)))

        return highest + 1

    def get_title(self, media_file: Path, info: dict) -> str:
        title = info.get("title")

        if title:
            return title

        name = media_file.stem

        if " - " in name:
            return name.split(" - ", 1)[1]

        return name

    def clean_filename(self, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', " ", str(name))
        name = re.sub(r"\s+", " ", name)
        name = name.strip(" .")

        if not name:
            return "Ohne Titel"

        return name[:160]

    def load_json(self, path: Path) -> dict:
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    def write_xml(self, path: Path, root: ET.Element):
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ", level=0)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def move_file(self, source: Path, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            destination.unlink()

        shutil.move(str(source), str(destination))

    def clean_work_dir(self, work_dir: Path, log_callback=None):
        if log_callback:
            log_callback("Räume Arbeitsordner auf...")

        for path in sorted(work_dir.rglob("*"), reverse=True):
            if path.is_file():
                if path.name.lower() != "archive.txt":
                    path.unlink(missing_ok=True)
            elif path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass

    def _extract_percent(self, data) -> int:
        total = data.get("total_bytes") or data.get("total_bytes_estimate")
        downloaded = data.get("downloaded_bytes")

        if total and downloaded:
            return int((downloaded / total) * 100)

        percent_text = data.get("_percent_str", "").replace("%", "").strip()

        try:
            return int(float(percent_text))
        except Exception:
            return 0