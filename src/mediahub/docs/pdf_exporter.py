import html
from pathlib import Path

from src.mediahub.docs.markdown_tools import MarkdownTools


class PdfExporter:
    def __init__(self):
        self.tools = MarkdownTools()

    def write(self, book, docs, figures, lookup, target: Path):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Image,
                PageBreak,
            )
            from reportlab.lib.styles import getSampleStyleSheet
        except Exception:
            print("⚠ reportlab fehlt. PDF wird übersprungen.")
            return

        pdf = SimpleDocTemplate(
            str(target),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(html.escape(book.title), styles["Title"]))
        story.append(Spacer(1, 18))

        story.append(Paragraph("Inhaltsverzeichnis", styles["Heading1"]))
        for doc in docs:
            story.append(Paragraph(f"• {html.escape(doc['title'])}", styles["BodyText"]))

        if figures:
            story.append(Spacer(1, 18))
            story.append(Paragraph("Abbildungsverzeichnis", styles["Heading1"]))
            for fig in figures:
                story.append(
                    Paragraph(
                        f"Abbildung {fig['number']}: {html.escape(fig['caption'])}",
                        styles["BodyText"],
                    )
                )

        story.append(PageBreak())

        for doc in docs:
            for line in doc["text"].splitlines():
                clean = line.strip()
                ref = self.tools.image_reference(clean)

                if ref:
                    image_name, _caption = ref
                    fig = self.tools.image_figure(doc, lookup, image_name)

                    if fig and fig["exists"]:
                        try:
                            img = Image(str(fig["path"]))
                            img._restrictSize(16 * cm, 10 * cm)
                            story.append(img)
                            story.append(
                                Paragraph(
                                    f"Abbildung {fig['number']}: "
                                    f"{html.escape(fig['caption'])}",
                                    styles["Italic"],
                                )
                            )
                        except Exception as error:
                            story.append(
                                Paragraph(
                                    f"Bild konnte nicht eingefügt werden: "
                                    f"{html.escape(str(error))}",
                                    styles["BodyText"],
                                )
                            )
                    elif fig:
                        story.append(
                            Paragraph(
                                f"Abbildung {fig['number']} fehlt: "
                                f"{html.escape(fig['path'].name)}",
                                styles["BodyText"],
                            )
                        )

                    story.append(Spacer(1, 10))
                    continue

                if clean.startswith("# "):
                    story.append(Paragraph(html.escape(clean[2:]), styles["Heading1"]))
                elif clean.startswith("## "):
                    story.append(Paragraph(html.escape(clean[3:]), styles["Heading2"]))
                elif clean.startswith("### "):
                    story.append(Paragraph(html.escape(clean[4:]), styles["Heading3"]))
                elif clean.startswith("- "):
                    story.append(
                        Paragraph("• " + html.escape(clean[2:]), styles["BodyText"])
                    )
                elif clean:
                    story.append(Paragraph(html.escape(clean), styles["BodyText"]))
                else:
                    story.append(Spacer(1, 6))

        pdf.build(story)
