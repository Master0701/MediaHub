from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as exc:
    raise SystemExit(
        "Pillow fehlt. Bitte installieren mit:\n\n"
        "python -m pip install pillow\n"
    ) from exc


DEFAULT_MANIFEST = Path("docs_source") / "screenshot_annotations.json"
DEFAULT_IMAGE_DIR = Path("docs_source") / "user" / "images"
DEFAULT_OUTPUT_DIR = Path("docs_source") / "user" / "images" / "marked"


def load_font(size: int):
    candidates = [
        "arial.ttf",
        "seguiemj.ttf",
        "DejaVuSans.ttf",
    ]

    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass

    return ImageFont.load_default()


def draw_marker(draw: ImageDraw.ImageDraw, x: int, y: int, number: int, radius: int, font):
    fill = (255, 216, 77)
    outline = (20, 20, 20)
    text_color = (0, 0, 0)

    left = x - radius
    top = y - radius
    right = x + radius
    bottom = y + radius

    draw.ellipse((left, top, right, bottom), fill=fill, outline=outline, width=3)

    text = str(number)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    draw.text(
        (x - tw / 2, y - th / 2 - 1),
        text,
        fill=text_color,
        font=font,
    )


def annotate_image(image_path: Path, output_path: Path, markers: list[dict], scale: float = 1.0):
    image = Image.open(image_path).convert("RGBA")

    if scale != 1.0:
        width = max(1, int(image.width * scale))
        height = max(1, int(image.height * scale))
        image = image.resize((width, height), Image.LANCZOS)

    draw = ImageDraw.Draw(image)
    radius = max(14, int(min(image.width, image.height) * 0.018))
    font = load_font(max(14, int(radius * 1.3)))

    for index, marker in enumerate(markers, start=1):
        number = int(marker.get("number", index))
        x = int(marker["x"] * scale)
        y = int(marker["y"] * scale)
        draw_marker(draw, x, y, number, radius, font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, quality=95)


def annotate_from_manifest(manifest_path: Path, image_dir: Path, output_dir: Path):
    if not manifest_path.exists():
        raise SystemExit(f"Manifest nicht gefunden: {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        entries = data.get("images", [])
    else:
        entries = data

    created = 0
    missing = 0

    for item in entries:
        filename = item.get("file") or item.get("filename")
        if not filename:
            continue

        markers = item.get("markers", [])
        if not markers:
            continue

        source = image_dir / filename
        target_name = item.get("output") or filename
        target = output_dir / target_name

        if not source.exists():
            print(f"⚠ fehlt: {source}")
            missing += 1
            continue

        annotate_image(source, target, markers)
        print(f"✅ markiert: {target}")
        created += 1

    print()
    print(f"Fertig. Erstellt: {created}, fehlend: {missing}")


def create_example_manifest(path: Path):
    example = {
        "images": [
            {
                "file": "01_startseite.png",
                "output": "01_startseite_marked.png",
                "caption": "Startseite mit Werkzeugleiste",
                "markers": [
                    {"number": 1, "label": "Wizard", "x": 70, "y": 55},
                    {"number": 2, "label": "Neu", "x": 125, "y": 55},
                    {"number": 3, "label": "Tools", "x": 185, "y": 55},
                    {"number": 4, "label": "PM", "x": 245, "y": 55},
                    {"number": 5, "label": "Vorschau", "x": 330, "y": 55},
                    {"number": 6, "label": "Videos", "x": 420, "y": 55},
                    {"number": 7, "label": "Sync", "x": 500, "y": 55},
                    {"number": 8, "label": "Stop", "x": 565, "y": 55},
                    {"number": 9, "label": "Hilfe", "x": 630, "y": 55}
                ]
            }
        ]
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(example, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"Beispiel-Manifest erstellt: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Markiert MediaHub-Screenshots mit nummerierten Kreisen."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Pfad zur screenshot_annotations.json",
    )
    parser.add_argument(
        "--image-dir",
        default=str(DEFAULT_IMAGE_DIR),
        help="Ordner mit Original-Screenshots",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Zielordner für markierte Screenshots",
    )
    parser.add_argument(
        "--create-example",
        action="store_true",
        help="Erstellt ein Beispiel-Manifest.",
    )

    args = parser.parse_args()

    manifest = Path(args.manifest)
    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)

    if args.create_example:
        create_example_manifest(manifest)
        return

    annotate_from_manifest(manifest, image_dir, output_dir)


if __name__ == "__main__":
    main()
