import html
from pathlib import Path

from src.mediahub.docs.constants import IMAGE_TOKEN, MARKDOWN_IMAGE_TOKEN


class MarkdownTools:
    def clean_markdown_line(self, line: str) -> str:
        line = line.strip()

        if line.startswith("# "):
            return line[2:].strip().upper()

        if line.startswith("## "):
            return line[3:].strip()

        if line.startswith("### "):
            return line[4:].strip()

        if line.startswith("- "):
            return "  - " + line[2:].strip()

        return line

    def image_reference(self, line: str):
        """Erkennt MediaHub-Bildtoken und normale Markdown-Bilder."""
        clean = line.strip()

        match = IMAGE_TOKEN.search(clean)
        if match:
            image_name = match.group(1).strip()
            caption = (match.group(2) or Path(image_name).stem).strip()
            return image_name, caption

        match = MARKDOWN_IMAGE_TOKEN.search(clean)
        if match:
            caption = (match.group(1) or "Bild").strip()
            image_name = match.group(2).strip()

            if image_name.startswith("images/"):
                image_name = image_name[len("images/"):]
            elif image_name.startswith("./images/"):
                image_name = image_name[len("./images/"):]

            return image_name, caption

        return None

    def image_figure(self, doc, lookup, image_name: str):
        image_name = image_name.strip()
        return lookup.get((doc["key"], image_name)) or lookup.get(
            (doc["key"], Path(image_name).stem)
        )

    def to_plain(self, doc, lookup) -> str:
        lines = []

        for line in doc["text"].splitlines():
            ref = self.image_reference(line)

            if ref:
                image_name, _caption = ref
                fig = self.image_figure(doc, lookup, image_name)

                if fig:
                    if fig["exists"]:
                        lines.append(f"Abbildung {fig['number']}: {fig['caption']}")
                    else:
                        lines.append(
                            f"Abbildung {fig['number']} fehlt: {fig['path'].name}"
                        )

                lines.append("")
                continue

            lines.append(self.clean_markdown_line(line))

        return "\n".join(lines).strip()

    def to_html(self, doc, lookup) -> str:
        out = []

        for line in doc["text"].splitlines():
            clean = line.strip()
            ref = self.image_reference(clean)

            if ref:
                image_name, _caption = ref
                fig = self.image_figure(doc, lookup, image_name)

                if fig and fig["exists"]:
                    rel = f"images/{fig['path'].name}"
                    caption = html.escape(
                        f"Abbildung {fig['number']}: {fig['caption']}"
                    )
                    alt = html.escape(fig["caption"])

                    out.append(
                        f'<figure id="fig-{fig["number"]}">'
                        f'<img src="{rel}" alt="{alt}">'
                        f"<figcaption>{caption}</figcaption>"
                        f"</figure>"
                    )
                elif fig:
                    out.append(
                        f'<p class="missing">Abbildung {fig["number"]} fehlt: '
                        f'{html.escape(fig["path"].name)}</p>'
                    )

                continue

            if clean.startswith("# "):
                out.append(f"<h1>{html.escape(clean[2:])}</h1>")
            elif clean.startswith("## "):
                out.append(f"<h2>{html.escape(clean[3:])}</h2>")
            elif clean.startswith("### "):
                out.append(f"<h3>{html.escape(clean[4:])}</h3>")
            elif clean.startswith("- "):
                out.append(f"<p>• {html.escape(clean[2:])}</p>")
            elif clean:
                out.append(f"<p>{html.escape(clean)}</p>")
            else:
                out.append("")

        return "\n".join(out)
