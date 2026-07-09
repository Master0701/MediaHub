from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None


def image_signature(path: Path, size=(16, 16)):
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


def images_look_same(a: Path, b: Path, tolerance=24) -> bool:
    try:
        if not a.exists() or not b.exists():
            return False

        if a.resolve() == b.resolve():
            return True

        if a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes():
            return True

        sig_a = image_signature(a)
        sig_b = image_signature(b)

        if sig_a is None or sig_b is None or len(sig_a) != len(sig_b):
            return False

        diff = 0
        for pa, pb in zip(sig_a, sig_b):
            diff += abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])

        return diff <= tolerance
    except Exception:
        return False


def write_index(channel_dir: Path):
    playlists_dir = channel_dir / "playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)

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


def clean_channel(channel_dir: Path, dry_run: bool = False) -> dict:
    playlists_dir = channel_dir / "playlists"
    invalid_dir = channel_dir / "_invalid_playlist_images"

    result = {
        "checked": 0,
        "moved": 0,
        "kept": 0,
        "reason": [],
    }

    if not playlists_dir.exists():
        write_index(channel_dir)
        return result

    compare_images = []
    for name in ("channel.jpg", "banner.jpg"):
        path = channel_dir / name
        if path.exists():
            compare_images.append(path)

    for playlist_image in sorted(playlists_dir.glob("*.jpg")):
        result["checked"] += 1
        wrong = False
        reason = ""

        for other in compare_images:
            if images_look_same(playlist_image, other):
                wrong = True
                reason = f"identisch/ähnlich zu {other.name}"
                break

        if wrong:
            result["moved"] += 1
            result["reason"].append(f"{playlist_image.name}: {reason}")
            if not dry_run:
                invalid_dir.mkdir(parents=True, exist_ok=True)
                target = invalid_dir / playlist_image.name
                if target.exists():
                    target = invalid_dir / f"{playlist_image.stem}_old{playlist_image.suffix}"
                shutil.move(str(playlist_image), str(target))
        else:
            result["kept"] += 1

    if not dry_run:
        write_index(channel_dir)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Verschiebt falsche Playlistbilder, die wie Kanalbild/Banner aussehen."
    )
    parser.add_argument("--root", default=".", help="MediaHub-Hauptordner")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts verschieben")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    assets = root / "assets" / "channels"

    print("MediaHub falsche Playlistbilder bereinigen")
    print(f"Root:   {root}")
    print(f"Assets: {assets}")
    print(f"Modus:  {'Nur prüfen' if args.dry_run else 'Verschieben'}")
    print()

    if Image is None:
        print("⚠ Pillow ist nicht installiert. Es wird nur exakte Dateigleichheit erkannt.")
        print("Empfohlen: python -m pip install pillow")
        print()

    if not assets.exists():
        print("❌ assets/channels existiert nicht.")
        return

    total_checked = total_moved = total_kept = 0

    for channel_dir in sorted(p for p in assets.iterdir() if p.is_dir()):
        result = clean_channel(channel_dir, dry_run=args.dry_run)

        total_checked += result["checked"]
        total_moved += result["moved"]
        total_kept += result["kept"]

        print(
            f"{channel_dir.name}: geprüft={result['checked']}, "
            f"verschoben={result['moved']}, behalten={result['kept']}"
        )
        for item in result["reason"][:10]:
            print(f"  - {item}")
        if len(result["reason"]) > 10:
            print(f"  ... {len(result['reason']) - 10} weitere")

    print()
    print(f"Gesamt: geprüft={total_checked}, verschoben={total_moved}, behalten={total_kept}")
    print()

    if args.dry_run:
        print("Es wurde nichts geändert.")
    else:
        print("Falsche Bilder liegen jetzt in _invalid_playlist_images und wurden nicht gelöscht.")
        print("Danach prüfen mit: python tools\\check_mediahub_images.py")


if __name__ == "__main__":
    main()
