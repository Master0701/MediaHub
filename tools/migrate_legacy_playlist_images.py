from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def migrate_channel(channel_dir: Path, move: bool = False) -> dict:
    playlists_dir = channel_dir / "playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0

    for source in sorted(channel_dir.glob("playlist_*.jpg")):
        playlist_id = source.stem.replace("playlist_", "", 1).strip()
        if not playlist_id:
            skipped += 1
            continue

        target = playlists_dir / f"{playlist_id}.jpg"

        if target.exists():
            skipped += 1
            continue

        if move:
            shutil.move(str(source), str(target))
        else:
            shutil.copy2(str(source), str(target))

        copied += 1

    data = {
        "channel": "channel.jpg" if (channel_dir / "channel.jpg").exists() else "",
        "banner": "banner.jpg" if (channel_dir / "banner.jpg").exists() else "",
        "playlists": {},
    }

    for path in sorted(playlists_dir.glob("*.jpg")):
        data["playlists"][path.stem] = f"playlists/{path.name}"

    (channel_dir / "images.json").write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "copied": copied,
        "skipped": skipped,
        "playlists": len(data["playlists"]),
        "channel": bool(data["channel"]),
        "banner": bool(data["banner"]),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Übernimmt alte playlist_<ID>.jpg Bilder in assets/channels/<Kanal>/playlists."
    )
    parser.add_argument("--root", default=".", help="MediaHub-Hauptordner")
    parser.add_argument(
        "--move",
        action="store_true",
        help="Alte playlist_<ID>.jpg Dateien verschieben statt kopieren.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    assets = root / "assets" / "channels"

    print("MediaHub alte Playlistbilder übernehmen")
    print(f"Root:   {root}")
    print(f"Assets: {assets}")
    print()

    if not assets.exists():
        print("❌ assets/channels existiert nicht.")
        return

    channel_dirs = [p for p in sorted(assets.iterdir()) if p.is_dir()]

    total_copied = 0

    for channel_dir in channel_dirs:
        result = migrate_channel(channel_dir, move=args.move)
        total_copied += result["copied"]

        print(
            f"{channel_dir.name}: "
            f"übernommen={result['copied']}, "
            f"übersprungen={result['skipped']}, "
            f"playlistbilder={result['playlists']}, "
            f"channel={'OK' if result['channel'] else 'FEHLT'}, "
            f"banner={'OK' if result['banner'] else 'FEHLT'}"
        )

    print()
    print(f"Fertig. Übernommene Playlistbilder: {total_copied}")
    print()
    print("Danach prüfen mit:")
    print("python tools\\check_mediahub_images.py")


if __name__ == "__main__":
    main()
