from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_index(channel_dir: Path) -> dict:
    playlists_dir = channel_dir / "playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "channel": "channel.jpg" if (channel_dir / "channel.jpg").exists() else "",
        "banner": "banner.jpg" if (channel_dir / "banner.jpg").exists() else "",
        "playlists": {},
    }

    for path in sorted(playlists_dir.glob("*.jpg")):
        data["playlists"][path.stem] = f"playlists/{path.name}"

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Repariert die MediaHub-Bildstruktur unter assets/channels."
    )
    parser.add_argument("--root", default=".", help="MediaHub-Hauptordner")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    assets = root / "assets" / "channels"

    print("MediaHub Bildstruktur reparieren")
    print(f"Root:   {root}")
    print(f"Assets: {assets}")
    print()

    if not assets.exists():
        print("assets/channels existiert noch nicht. Ordner wird angelegt.")
        assets.mkdir(parents=True, exist_ok=True)

    channel_dirs = [p for p in sorted(assets.iterdir()) if p.is_dir()]

    if not channel_dirs:
        print("Keine Kanal-Bildordner gefunden.")
        return

    created_indexes = 0
    created_playlist_dirs = 0

    for channel_dir in channel_dirs:
        playlists_dir = channel_dir / "playlists"
        if not playlists_dir.exists():
            playlists_dir.mkdir(parents=True, exist_ok=True)
            created_playlist_dirs += 1

        data = build_index(channel_dir)
        index_path = channel_dir / "images.json"
        index_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        created_indexes += 1

        channel_status = "OK" if data["channel"] else "FEHLT"
        banner_status = "OK" if data["banner"] else "FEHLT"
        playlist_count = len(data["playlists"])

        print(
            f"{channel_dir.name}: "
            f"channel={channel_status}, banner={banner_status}, "
            f"playlistbilder={playlist_count}, images.json=OK"
        )

    print()
    print("Fertig.")
    print(f"Playlist-Ordner angelegt: {created_playlist_dirs}")
    print(f"images.json geschrieben: {created_indexes}")
    print()
    print("Hinweis:")
    print("Dieses Tool löscht nichts. Es registriert nur vorhandene Bilder.")
    print("Playlistbilder entstehen erst, wenn Playlists über den Assistenten/Playlist-Manager neu geladen werden.")


if __name__ == "__main__":
    main()
