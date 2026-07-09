from __future__ import annotations

import json
from pathlib import Path

from src.mediahub.docs.config import SOURCE_DIR


ANNOTATION_FILE = SOURCE_DIR / "screenshot_annotations.json"
USER_IMAGE_DIR = SOURCE_DIR / "user" / "images"
MARKED_DIR_NAME = "marked"


def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont
    except Exception:
        return None, None, None


def _font(size: int, image_font):
    candidates = [
        "arial.ttf",
        "seguiemj.ttf",
        "DejaVuSans.ttf",
    ]

    for name in candidates:
        try:
            return image_font.truetype(name, size)
        except Exception:
            pass

    return image_font.load_default()


def _read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"⚠ Screenshot-Markierungen konnten nicht gelesen werden: {exc}")
        return []

    if isinstance(data, dict):
        items = data.get("images", [])
    elif isinstance(data, list):
        items = data
    else:
        items = []

    if not isinstance(items, list):
        return []

    return [item for item in items if isinstance(item, dict)]


def _marker_position(marker: dict) -> tuple[int, int] | None:
    try:
        return int(marker["x"]), int(marker["y"])
    except Exception:
        return None


def _draw_marker(draw, x: int, y: int, number: int, radius: int, font):
    fill = (255, 216, 77)
    outline = (20, 20, 20)
    text_color = (0, 0, 0)

    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=fill,
        outline=outline,
        width=max(2, radius // 6),
    )

    text = str(number)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw = len(text) * radius * 0.6
        th = radius

    draw.text(
        (x - tw / 2, y - th / 2 - 1),
        text,
        fill=text_color,
        font=font,
    )


def _annotate_one(source: Path, target: Path, markers: list[dict], image, image_draw, image_font):
    img = image.open(source).convert("RGBA")
    draw = image_draw.Draw(img)

    radius = max(14, int(min(img.width, img.height) * 0.018))
    font = _font(max(14, int(radius * 1.25)), image_font)

    for index, marker in enumerate(markers, start=1):
        pos = _marker_position(marker)
        if pos is None:
            continue

        number = int(marker.get("number", index))
        x, y = pos
        _draw_marker(draw, x, y, number, radius, font)

    target.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(target, quality=95)


def annotate_all_images(
    manifest_path: Path | None = None,
    image_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    """Erzeugt markierte Screenshots für die Dokumentation.

    Originalbilder werden nie überschrieben.
    Wenn Pillow nicht installiert ist, wird der Schritt übersprungen,
    damit build_docs.py weiterhin normal durchläuft.
    """
    manifest_path = Path(manifest_path or ANNOTATION_FILE)
    image_dir = Path(image_dir or USER_IMAGE_DIR)
    output_dir = Path(output_dir or (image_dir / MARKED_DIR_NAME))

    entries = _read_manifest(manifest_path)

    result = {
        "enabled": bool(entries),
        "created": 0,
        "missing": 0,
        "skipped": 0,
        "errors": 0,
    }

    if not entries:
        print("ℹ Keine Screenshot-Markierungen definiert.")
        return result

    image, image_draw, image_font = _load_pillow()

    if image is None:
        print("⚠ Pillow fehlt. Screenshot-Markierungen werden übersprungen.")
        print("  Installieren mit: python -m pip install pillow")
        result["skipped"] = len(entries)
        return result

    print()
    print("🖼 Markiere Screenshots")

    for item in entries:
        filename = item.get("file") or item.get("filename")
        if not filename:
            result["skipped"] += 1
            continue

        markers = item.get("markers", [])
        if not markers:
            result["skipped"] += 1
            continue

        source = image_dir / filename
        output_name = item.get("output") or filename
        target = output_dir / output_name

        if not source.exists():
            print(f"⚠ fehlt: {source}")
            result["missing"] += 1
            continue

        try:
            _annotate_one(source, target, markers, image, image_draw, image_font)
            print(f"✔ {target}")
            result["created"] += 1
        except Exception as exc:
            print(f"⚠ Fehler bei {source.name}: {exc}")
            result["errors"] += 1

    print(
        f"✔ Screenshot-Markierungen: {result['created']} erstellt, "
        f"{result['missing']} fehlen, {result['skipped']} übersprungen"
    )

    return result
