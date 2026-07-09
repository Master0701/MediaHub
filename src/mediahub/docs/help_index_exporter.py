import json

from src.mediahub.docs.markdown_tools import MarkdownTools


class HelpIndexExporter:
    def __init__(self):
        self.tools = MarkdownTools()

    def write(self, book, docs, lookup, target):
        entries = []

        for doc in docs:
            plain = self.tools.to_plain(doc, lookup)
            entries.append(
                {
                    "key": doc["key"],
                    "title": doc["title"],
                    "book": book.key,
                    "keywords": plain.lower(),
                    "text": plain,
                    "source": doc["file"],
                }
            )

        target.write_text(
            json.dumps(entries, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )