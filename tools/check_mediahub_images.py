from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CHANNEL_FILES = [
    "channel.jpg",
    "banner.jpg",
]

EXPECTED_PLEX_SERIES_FILES = [
    "poster.jpg",
    "fanart.jpg",
    "tvshow.nfo",
]


def file_info(path: Path) -> str:
    if not path.exists():
        return "FEHLT"

    if path.is_dir():
        return "ORDNER"

    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    if size >= 1024 * 1024:
        return f"OK ({size / (1024 * 1024):.1f} MB)"
    if size >= 1024:
        return f"OK ({size / 1024:.1f} KB)"
    return f"OK ({size} B)"


def print_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def check_assets(root: Path):
    assets_dir = root / "assets" / "channels"

    print_header("1) Lokale MediaHub-Bilder")
    print(f"Ordner: {assets_dir}")

    if not assets_dir.exists():
        print("❌ assets/channels existiert nicht.")
        return

    channel_dirs = [p for p in sorted(assets_dir.iterdir()) if p.is_dir()]

    if not channel_dirs:
        print("❌ Keine Kanal-Bildordner gefunden.")
        return

    for channel_dir in channel_dirs:
        print()
        print(f"Kanalordner: {channel_dir.name}")

        for filename in EXPECTED_CHANNEL_FILES:
            path = channel_dir / filename
            icon = "✅" if path.exists() else "⚠"
            print(f"{icon} {filename}: {file_info(path)}")

        manifest = channel_dir / "images.json"
        icon = "✅" if manifest.exists() else "⚠"
        print(f"{icon} images.json: {file_info(manifest)}")

        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                playlists = data.get("playlists", {})
                print(f"   Playlists im Manifest: {len(playlists)}")
            except Exception as error:
                print(f"   ⚠ images.json konnte nicht gelesen werden: {error}")

        playlist_dir = channel_dir / "playlists"
        if playlist_dir.exists():
            playlist_images = sorted(playlist_dir.glob("*.jpg"))
            print(f"✅ playlist-Bilder: {len(playlist_images)}")
            for image in playlist_images[:20]:
                print(f"   - {image.name}: {file_info(image)}")
            if len(playlist_images) > 20:
                print(f"   ... {len(playlist_images) - 20} weitere")
        else:
            print("⚠ playlists-Ordner fehlt")


def check_plex_target(path: Path):
    print_header("2) Plex-Zielordner")
    print(f"Ordner: {path}")

    if not path.exists():
        print("❌ Plex-Zielordner existiert nicht.")
        return

    series_dirs = [p for p in sorted(path.iterdir()) if p.is_dir()]

    if not series_dirs:
        print("❌ Keine Serienordner gefunden.")
        return

    for series_dir in series_dirs:
        print()
        print(f"Serie: {series_dir.name}")

        for filename in EXPECTED_PLEX_SERIES_FILES:
            file_path = series_dir / filename
            icon = "✅" if file_path.exists() else "⚠"
            print(f"{icon} {filename}: {file_info(file_path)}")

        season_dirs = [
            p for p in sorted(series_dir.iterdir())
            if p.is_dir() and (
                p.name.lower().startswith("season")
                or p.name.lower().startswith("staffel")
                or True
            )
        ]

        if not season_dirs:
            print("⚠ Keine Staffel-/Playlistordner gefunden.")
            continue

        for season_dir in season_dirs[:20]:
            poster = season_dir / "poster.jpg"
            icon = "✅" if poster.exists() else "⚠"
            print(f"   {icon} {season_dir.name}/poster.jpg: {file_info(poster)}")

            episode_jpgs = [
                p for p in season_dir.glob("*.jpg")
                if p.name.lower() != "poster.jpg"
            ]
            episode_nfos = [
                p for p in season_dir.glob("*.nfo")
                if p.name.lower() != "tvshow.nfo"
            ]
            media_files = [
                p for p in season_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {
                    ".mkv", ".mp4", ".webm", ".avi", ".mov",
                    ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wav"
                }
            ]

            print(
                f"      Folgen: {len(media_files)} Medien, "
                f"{len(episode_jpgs)} JPG-Bilder, {len(episode_nfos)} NFO-Dateien"
            )

        if len(season_dirs) > 20:
            print(f"   ... {len(season_dirs) - 20} weitere Ordner")


def main():
    parser = argparse.ArgumentParser(
        description="Prüft MediaHub-Bildverwaltung und Plex-Zielordner."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="MediaHub-Projekt-/Installationsordner. Standard: aktueller Ordner.",
    )
    parser.add_argument(
        "--plex",
        default="",
        help="Optional: Plex-Zielordner prüfen.",
    )

    args = parser.parse_args()

    root = Path(args.root).resolve()
    print("MediaHub Bilddiagnose")
    print(f"Root: {root}")

    check_assets(root)

    if args.plex:
        check_plex_target(Path(args.plex).resolve())
    else:
        print_header("2) Plex-Zielordner")
        print("Nicht geprüft. Nutze z. B.:")
        print('python tools\\check_mediahub_images.py --plex "D:\\Plex\\Serien"')


if __name__ == "__main__":
    main()
