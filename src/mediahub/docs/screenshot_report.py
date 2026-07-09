from __future__ import annotations

from pathlib import Path

from src.mediahub.docs.screenshot_catalog import scan_screenshots


OPTIONAL_SCREENSHOTS = {
    "08_preview.png",
}


def _is_optional(item: dict) -> bool:
    filename = item.get("filename", "")

    if item.get("optional", False):
        return True

    return filename in OPTIONAL_SCREENSHOTS


def build_screenshot_report(base_dir: Path) -> str:
    items = scan_screenshots(base_dir)

    required_items = [item for item in items if not _is_optional(item)]
    optional_items = [item for item in items if _is_optional(item)]

    existing = [item for item in required_items if item.get("exists")]
    missing = [item for item in required_items if not item.get("exists")]

    optional_existing = [item for item in optional_items if item.get("exists")]
    optional_missing = [item for item in optional_items if not item.get("exists")]

    lines = [
        "MediaHub Screenshot-Bericht",
        "=" * 30,
        "",
        f"Vorhanden: {len(existing)}",
        f"Fehlend:   {len(missing)}",
        f"Optional:  {len(optional_items)}",
        "",
        "Vorhandene Screenshots:",
    ]

    if existing:
        for item in existing:
            lines.append(f"✅ {item['filename']} - {item.get('title', '')}")
    else:
        lines.append("Keine Screenshots vorhanden.")

    lines.extend(["", "Fehlende Screenshots:"])

    if missing:
        for item in missing:
            lines.append(f"⚠ {item['filename']} - {item.get('title', '')}")
    else:
        lines.append("Keine Screenshots fehlen.")

    if optional_items:
        lines.extend(["", "Optionale Screenshots:"])

        for item in optional_existing:
            lines.append(f"✅ optional: {item['filename']} - {item.get('title', '')}")

        for item in optional_missing:
            lines.append(f"ℹ optional fehlt: {item['filename']} - {item.get('title', '')}")

    return "\n".join(lines)
