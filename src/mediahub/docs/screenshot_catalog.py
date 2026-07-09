from __future__ import annotations

import re
from pathlib import Path


# Fallback-Liste, falls noch keine Markdown-Dateien vorhanden sind.
# Sobald docs_source/user/*.md existiert, wird der Katalog automatisch aus
# den tatsächlich verwendeten Bildern im Handbuch erzeugt.
USER_SCREENSHOTS = [
    {"filename": "01_startseite.png", "title": "Startseite"},
    {"filename": "02_menueleiste.png", "title": "Menüleiste"},
    {"filename": "03_toolbar.png", "title": "Toolbar"},
    {"filename": "04_kanalliste.png", "title": "Kanalliste"},
    {"filename": "05_dashboard.png", "title": "Dashboard"},
    {"filename": "06_log.png", "title": "Log"},
    {"filename": "07_statusleiste.png", "title": "Statusleiste"},
]

MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<title>[^\]]*)\]\((?P<path>[^)]+)\)")
IMAGE_TOKEN_RE = re.compile(r"\[\[\s*(?:image|IMAGE)\s*:\s*(?P<name>[^\]]+)\s*\]\]")


def user_docs_dir(base_dir: Path) -> Path:
    return Path(base_dir) / "docs_source" / "user"


def screenshot_image_dir(base_dir: Path) -> Path:
    return user_docs_dir(base_dir) / "images"


def _split_token_value(value: str) -> tuple[str, str]:
    text = (value or "").strip().strip('"').strip("'")

    if "|" in text:
        name, caption = text.split("|", 1)
        return name.strip(), caption.strip()

    return text, ""


def _clean_image_name(value: str) -> str:
    text, _caption = _split_token_value(value)

    # Markdown-Bilder können relative Pfade wie images/05_dashboard.png enthalten.
    # Für den Katalog zählt nur der Dateiname im images-Ordner.
    filename = Path(text).name

    # Alte MediaHub-Tokens nutzen oft nur den Bildschlüssel ohne Endung,
    # z. B. [[IMAGE:05_dashboard|...]]. Im images-Ordner liegen PNG-Dateien.
    if filename and "." not in filename:
        filename = f"{filename}.png"

    return filename


def _add_unique(items: list[dict], filename: str, title: str) -> None:
    if not filename:
        return

    for item in items:
        if item["filename"] == filename:
            if title and not item.get("title"):
                item["title"] = title
            return

    items.append(
        {
            "filename": filename,
            "title": title or Path(filename).stem.replace("_", " ").title(),
        }
    )


def referenced_screenshots(base_dir: Path) -> list[dict]:
    """Liest alle im Benutzerhandbuch verwendeten Screenshots aus Markdown."""
    docs_dir = user_docs_dir(base_dir)

    if not docs_dir.exists():
        return []

    items: list[dict] = []

    for file in sorted(docs_dir.glob("*.md")):
        try:
            text = file.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in MARKDOWN_IMAGE_RE.finditer(text):
            filename = _clean_image_name(match.group("path"))
            title = (match.group("title") or "").strip()
            _add_unique(items, filename, title)

        for match in IMAGE_TOKEN_RE.finditer(text):
            raw_name = match.group("name")
            filename = _clean_image_name(raw_name)
            _name, caption = _split_token_value(raw_name)
            _add_unique(items, filename, caption)

    return items


def screenshot_catalog(base_dir: Path) -> list[dict]:
    """Gibt den aktiven Screenshot-Katalog zurück.

    Wenn im Benutzerhandbuch Bilder verwendet werden, ist das Handbuch die
    einzige Quelle der Wahrheit. Die feste Liste wird nur als Fallback genutzt.
    """
    found = referenced_screenshots(base_dir)

    if found:
        return found

    return list(USER_SCREENSHOTS)


OPTIONAL_SCREENSHOTS = {
    '08_preview.png',
}


def scan_screenshots(base_dir: Path) -> list[dict]:
    image_dir = screenshot_image_dir(base_dir)
    result = []

    for item in screenshot_catalog(base_dir):
        filename = item["filename"]
        path = image_dir / filename

        result.append(
            {
                "filename": filename,
                "title": item.get("title", ""),
                "path": str(path),
                "exists": path.exists(),
                "required": filename not in OPTIONAL_SCREENSHOTS,
            }
        )

    return result


def missing_screenshots(base_dir: Path) -> list[dict]:
    return [item for item in scan_screenshots(base_dir) if item.get('required', True) and not item.get('exists')]
