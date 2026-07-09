from src.mediahub.docs.config import APP_VERSION
from src.mediahub.docs.markdown_tools import MarkdownTools


class TxtExporter:
    def __init__(self):
        self.tools = MarkdownTools()

    def write(self, book, docs, figures, lookup, target):
        parts = [
            f"{book.title} v{APP_VERSION}",
            "=" * 60,
            "",
            "INHALTSVERZEICHNIS",
            "-" * 60,
        ]

        for doc in docs:
            parts.append(f"- {doc['title']}")

        if figures:
            parts.extend(["", "ABBILDUNGSVERZEICHNIS", "-" * 60])
            for fig in figures:
                parts.append(f"Abbildung {fig['number']}: {fig['caption']}")

        parts.append("")
        parts.append("=" * 60)
        parts.append("")

        for doc in docs:
            parts.append(self.tools.to_plain(doc, lookup))
            parts.append("")
            parts.append("-" * 60)
            parts.append("")

        target.write_text("\n".join(parts), encoding="utf-8")