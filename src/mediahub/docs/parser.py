from src.mediahub.docs.models import DocBook


class MarkdownParser:
    def read_docs(self, book: DocBook):
        docs = []

        for file in sorted(book.source_dir.glob("*.md")):
            text = file.read_text(encoding="utf-8")
            title = file.stem

            for line in text.splitlines():
                if line.strip().startswith("# "):
                    title = line.strip()[2:].strip()
                    break

            docs.append(
                {
                    "file": file.name,
                    "key": file.stem,
                    "title": title,
                    "text": text,
                }
            )

        return docs