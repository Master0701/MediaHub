import html

from src.mediahub.docs.config import APP_VERSION
from src.mediahub.docs.markdown_tools import MarkdownTools


class HtmlExporter:
    def __init__(self):
        self.tools = MarkdownTools()

    def write(self, book, docs, figures, lookup, target):
        body = []

        body.append(f"<h1>{html.escape(book.title)} v{APP_VERSION}</h1>")

        body.append("<h2>Inhaltsverzeichnis</h2>")
        body.append("<ul>")
        for doc in docs:
            body.append(
                f'<li><a href="#{html.escape(doc["key"])}">'
                f'{html.escape(doc["title"])}</a></li>'
            )
        body.append("</ul>")

        if figures:
            body.append("<h2>Abbildungsverzeichnis</h2>")
            body.append("<ul>")
            for fig in figures:
                body.append(
                    f'<li><a href="#fig-{fig["number"]}">'
                    f'Abbildung {fig["number"]}: {html.escape(fig["caption"])}</a></li>'
                )
            body.append("</ul>")

        for doc in docs:
            body.append(f'<section id="{html.escape(doc["key"])}">')
            body.append(self.tools.to_html(doc, lookup))
            body.append("</section>")

        html_text = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{html.escape(book.title)}</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    background: #111;
    color: #eee;
    line-height: 1.6;
}}
a {{
    color: #ffd84d;
}}
h1 {{
    color: #ffd84d;
    border-bottom: 1px solid #444;
    padding-bottom: 10px;
}}
h2 {{
    color: #ffffff;
    margin-top: 30px;
}}
h3 {{
    color: #dddddd;
}}
p {{
    max-width: 980px;
}}
figure {{
    margin: 24px 0;
    padding: 14px;
    background: #1b1b1b;
    border: 1px solid #333;
    border-radius: 8px;
}}
figure img {{
    max-width: 100%;
    border-radius: 6px;
    border: 1px solid #444;
}}
figcaption {{
    margin-top: 8px;
    color: #ccc;
    font-size: 0.95em;
}}
.missing {{
    color: #ff7777;
    font-weight: bold;
}}
</style>
</head>
<body>
{chr(10).join(body)}
</body>
</html>
"""
        target.write_text(html_text, encoding="utf-8")