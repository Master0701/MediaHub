from __future__ import annotations

import json
from pathlib import Path


def markdown_to_plain(md: str) -> str:
    lines = []

    for line in md.splitlines():
        clean = line.strip()

        if clean.startswith("# "):
            lines.append(clean[2:].upper())
            lines.append("")
        elif clean.startswith("## "):
            lines.append(clean[3:])
            lines.append("")
        elif clean.startswith("### "):
            lines.append(clean[4:])
            lines.append("")
        elif clean.startswith("- "):
            lines.append("  - " + clean[2:])
        else:
            lines.append(line)

    return "\n".join(lines).strip()


def load_plugin_help(base_dir: Path) -> list[dict]:
    entries = []
    plugins_dir = Path(base_dir) / "plugins"

    if not plugins_dir.exists():
        return entries

    for help_file in sorted(plugins_dir.glob("*/help.md")):
        try:
            text = help_file.read_text(encoding="utf-8")
        except Exception:
            continue

        plugin_dir = help_file.parent
        title = plugin_dir.name
        manifest = plugin_dir / "plugin.json"

        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                title = data.get("name") or title
            except Exception:
                pass

        plain = markdown_to_plain(text)

        entries.append(
            {
                "title": title,
                "raw_title": title,
                "key": f"plugin_{plugin_dir.name}",
                "book": "plugin",
                "keywords": plain.lower(),
                "text": plain,
                "source": str(help_file),
            }
        )

    return entries