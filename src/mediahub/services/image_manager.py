from __future__ import annotations

import json
import re
import shutil
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None


class ImageAssetManager:
    """Zentrale Bildverwaltung für MediaHub.

    Dieser Manager ist die einzige Stelle, die Kanal-, Banner- und Playlistbilder
    lokal als JPG ablegt. Der Plex-Import soll später nur noch lokale Dateien
    kopieren, nicht mehr im Internet suchen.
    """

    POSTER_SIZE = (1000, 1500)
    FANART_SIZE = (1920, 1080)
    EPISODE_SIZE = (1280, 720)

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or Path.cwd())
        self.assets_dir = self.base_dir / "assets" / "channels"

    def safe_name(self, value: str) -> str:
        text = re.sub(r'[<>:"/\\|?*]+', "_", str(value or "")).strip()
        text = re.sub(r"\s+", "_", text)
        return text or "channel"

    def channel_dir(self, channel_name: str, channel_id: str = "") -> Path:
        key = self.safe_name(channel_id or channel_name)
        folder = self.assets_dir / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "playlists").mkdir(parents=True, exist_ok=True)
        return folder

    def channel_image_path(self, channel_name: str, channel_id: str = "") -> Path:
        return self.channel_dir(channel_name, channel_id) / "channel.jpg"

    def banner_image_path(self, channel_name: str, channel_id: str = "") -> Path:
        return self.channel_dir(channel_name, channel_id) / "banner.jpg"

    def playlist_image_path(self, channel_name: str, playlist_id: str, channel_id: str = "") -> Path:
        safe_id = self.safe_name(playlist_id or "playlist")
        return self.channel_dir(channel_name, channel_id) / "playlists" / f"{safe_id}.jpg"

    def save_channel_image(self, channel_name: str, source: str, channel_id: str = "") -> str:
        return self.save_image(source, self.channel_image_path(channel_name, channel_id), "poster")

    def save_banner_image(self, channel_name: str, source: str, channel_id: str = "") -> str:
        return self.save_image(source, self.banner_image_path(channel_name, channel_id), "fanart")

    def save_playlist_image(self, channel_name: str, playlist_id: str, source: str, channel_id: str = "") -> str:
        destination = self.playlist_image_path(channel_name, playlist_id, channel_id)
        saved = self.save_image(source, destination, "poster")

        if saved and not self.is_valid_playlist_image(channel_name, destination, channel_id):
            try:
                invalid_dir = destination.parent.parent / "_invalid_playlist_images"
                invalid_dir.mkdir(parents=True, exist_ok=True)
                destination.replace(invalid_dir / destination.name)
            except Exception:
                try:
                    destination.unlink(missing_ok=True)
                except Exception:
                    pass

            self.write_index(destination.parent.parent / "channel.jpg")
            return ""

        return saved

    def save_image(self, source: str, destination: Path, kind: str = "poster") -> str:
        source = str(source or "").strip()
        if not source:
            return ""

        temp_file = None
        try:
            if source.startswith("http://") or source.startswith("https://"):
                temp_file = destination.with_suffix(".download")
                request = urllib.request.Request(source, headers={"User-Agent": "MediaHub/1.0"})
                with urllib.request.urlopen(request, timeout=25) as response:
                    data = response.read()
                if not data:
                    return ""
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                temp_file.write_bytes(data)
                source_path = temp_file
            else:
                source_path = Path(source)
                if not source_path.exists() or not source_path.is_file():
                    return ""

            if self.copy_or_convert_to_jpg(source_path, destination, kind):
                self.write_index(destination)
                return str(destination)
            return ""
        finally:
            if temp_file is not None:
                try:
                    temp_file.unlink(missing_ok=True)
                except Exception:
                    pass

    def copy_or_convert_to_jpg(self, source: Path, destination: Path, kind: str = "poster") -> bool:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)

            if Image is None:
                if source.suffix.lower() in {".jpg", ".jpeg"}:
                    shutil.copy2(str(source), str(destination))
                    return destination.exists()
                return False

            with Image.open(source) as image:
                image = self.prepare_for_plex(image, kind)
                image.save(destination, "JPEG", quality=92, optimize=True)
            return destination.exists()
        except Exception:
            return False

    def prepare_for_plex(self, image, kind: str = "poster"):
        kind = str(kind or "poster").lower()
        if kind == "fanart":
            target_size = self.FANART_SIZE
        elif kind == "episode":
            target_size = self.EPISODE_SIZE
        else:
            target_size = self.POSTER_SIZE

        if image.mode in {"RGBA", "LA", "P"}:
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (0, 0, 0))
            alpha = image.getchannel("A") if "A" in image.getbands() else None
            background.paste(image, mask=alpha)
            image = background
        else:
            image = image.convert("RGB")

        # Wichtig: nicht abschneiden. Logo/Poster proportional einpassen.
        image.thumbnail(target_size, Image.LANCZOS)
        canvas = Image.new("RGB", target_size, (0, 0, 0))
        x = (target_size[0] - image.width) // 2
        y = (target_size[1] - image.height) // 2
        canvas.paste(image, (x, y))
        return canvas

    def write_index(self, changed_file: Path) -> None:
        channel_dir = changed_file.parent
        if channel_dir.name == "playlists":
            channel_dir = channel_dir.parent
        index_path = channel_dir / "images.json"

        data = {
            "channel": "channel.jpg" if (channel_dir / "channel.jpg").exists() else "",
            "banner": "banner.jpg" if (channel_dir / "banner.jpg").exists() else "",
            "playlists": {},
        }
        playlists_dir = channel_dir / "playlists"
        if playlists_dir.exists():
            for path in sorted(playlists_dir.glob("*.jpg")):
                data["playlists"][path.stem] = f"playlists/{path.name}"

        try:
            index_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


    def rebuild_all_indexes(self) -> dict:
        """Erzeugt fehlende images.json-Dateien neu.

        Diese Funktion verändert keine vorhandenen Bilder und löscht nichts.
        Sie legt nur fehlende playlists-Ordner und images.json-Dateien an.
        """
        result = {
            "channels": 0,
            "with_channel": 0,
            "with_banner": 0,
            "playlist_images": 0,
            "indexes": 0,
        }

        self.assets_dir.mkdir(parents=True, exist_ok=True)

        for channel_dir in sorted(self.assets_dir.iterdir()):
            if not channel_dir.is_dir():
                continue

            result["channels"] += 1
            playlists_dir = channel_dir / "playlists"
            playlists_dir.mkdir(parents=True, exist_ok=True)

            if (channel_dir / "channel.jpg").exists():
                result["with_channel"] += 1
            if (channel_dir / "banner.jpg").exists():
                result["with_banner"] += 1

            result["playlist_images"] += len(list(playlists_dir.glob("*.jpg")))
            self.write_index(channel_dir / "channel.jpg")
            result["indexes"] += 1

        return result


    def migrate_legacy_playlist_images(self, channel_dir: Path, move: bool = False) -> int:
        """Übernimmt alte playlist_<ID>.jpg Bilder in den neuen playlists-Ordner.

        Alte Struktur:
            assets/channels/<Kanal>/playlist_PL123.jpg

        Neue Struktur:
            assets/channels/<Kanal>/playlists/PL123.jpg

        Standard ist Kopieren, nicht Verschieben.
        """
        import shutil

        channel_dir = Path(channel_dir)
        playlist_dir = channel_dir / "playlists"
        playlist_dir.mkdir(parents=True, exist_ok=True)

        count = 0

        for source in sorted(channel_dir.glob("playlist_*.jpg")):
            playlist_id = source.stem.replace("playlist_", "", 1).strip()
            if not playlist_id:
                continue

            target = playlist_dir / f"{playlist_id}.jpg"

            if target.exists():
                continue

            if move:
                shutil.move(str(source), str(target))
            else:
                shutil.copy2(str(source), str(target))

            count += 1

        return count


    def image_signature(self, path: Path, size: tuple[int, int] = (16, 16)):
        """Kleine Bildsignatur für einfache Gleichheitsprüfung."""
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

    def images_look_same(self, a: Path, b: Path, tolerance: int = 24) -> bool:
        """Prüft, ob zwei Bilder gleich oder fast gleich aussehen."""
        try:
            a = Path(a)
            b = Path(b)

            if not a.exists() or not b.exists():
                return False

            if a.resolve() == b.resolve():
                return True

            if a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes():
                return True

            sig_a = self.image_signature(a)
            sig_b = self.image_signature(b)

            if sig_a is None or sig_b is None or len(sig_a) != len(sig_b):
                return False

            diff = 0
            for pa, pb in zip(sig_a, sig_b):
                diff += abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])

            return diff <= tolerance
        except Exception:
            return False

    def is_valid_playlist_image(self, channel_name: str, playlist_path: Path, channel_id: str = "") -> bool:
        """Playlistbild darf nicht identisch mit Kanalposter oder Banner sein."""
        playlist_path = Path(playlist_path)
        if not playlist_path.exists() or not playlist_path.is_file():
            return False

        channel_dir = self.channel_dir(channel_name, channel_id)

        for other in (channel_dir / "channel.jpg", channel_dir / "banner.jpg"):
            if other.exists() and self.images_look_same(playlist_path, other):
                return False

        return True
