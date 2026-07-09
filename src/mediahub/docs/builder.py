import shutil

from src.mediahub.docs.config import APP_DOCS_DIR, BOOKS, RELEASE_DOCS_DIR, SOURCE_DIR
from src.mediahub.docs.docx_exporter import DocxExporter
from src.mediahub.docs.help_index_exporter import HelpIndexExporter
from src.mediahub.docs.html_exporter import HtmlExporter
from src.mediahub.docs.image_annotator import annotate_all_images
from src.mediahub.docs.image_manager import ImageManager
from src.mediahub.docs.parser import MarkdownParser
from src.mediahub.docs.pdf_exporter import PdfExporter
from src.mediahub.docs.txt_exporter import TxtExporter
from src.mediahub.docs.screenshot_report import build_screenshot_report


class DocumentationBuilder:
    def __init__(self):
        self.parser = MarkdownParser()
        self.images = ImageManager()

        self.txt_exporter = TxtExporter()
        self.html_exporter = HtmlExporter()
        self.docx_exporter = DocxExporter()
        self.pdf_exporter = PdfExporter()
        self.help_index_exporter = HelpIndexExporter()

    def ensure_dirs(self):
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        APP_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        RELEASE_DOCS_DIR.mkdir(parents=True, exist_ok=True)

        for book in BOOKS:
            book.source_dir.mkdir(parents=True, exist_ok=True)
            book.image_dir.mkdir(parents=True, exist_ok=True)
            book.app_dir.mkdir(parents=True, exist_ok=True)
            book.release_dir.mkdir(parents=True, exist_ok=True)

    def build_all(self):
        print("📚 Baue MediaHub-Dokumentation 3.3")

        self.ensure_dirs()
        annotate_all_images()

        for book in BOOKS:
            self.build_book(book)

        print()
        print("✅ Dokumentation fertig.")
        print(build_screenshot_report(SOURCE_DIR.parent))
        print(f"App-Dokumente:     {APP_DOCS_DIR}")
        print(f"Release-Dokumente: {RELEASE_DOCS_DIR}")

    def build_book(self, book):
        print()
        print("=" * 60)
        print(f"📖 Baue {book.title}")
        print("=" * 60)

        docs = self.parser.read_docs(book)
        figures = self.images.collect_figures(book, docs)
        lookup = self.images.figure_lookup(figures)

        self.images.copy_images(book, book.app_dir)
        self.images.copy_images(book, book.release_dir)

        txt_path = book.app_dir / book.txt_name
        html_path = book.app_dir / book.html_name
        docx_path = book.app_dir / book.docx_name
        pdf_path = book.app_dir / book.pdf_name

        self.txt_exporter.write(book, docs, figures, lookup, txt_path)
        self.html_exporter.write(book, docs, figures, lookup, html_path)
        self.docx_exporter.write(book, docs, figures, lookup, docx_path)
        self.pdf_exporter.write(book, docs, figures, lookup, pdf_path)

        self._copy_if_exists(txt_path, book.release_dir / book.txt_name)
        self._copy_if_exists(html_path, book.release_dir / book.html_name)
        self._copy_if_exists(docx_path, book.release_dir / book.docx_name)
        self._copy_if_exists(pdf_path, book.release_dir / book.pdf_name)

        if book.index_name:
            self.help_index_exporter.write(
                book,
                docs,
                lookup,
                APP_DOCS_DIR / book.index_name,
            )

        print(f"✔ TXT:  {book.txt_name}")
        print(f"✔ HTML: {book.html_name}")
        print(f"✔ DOCX: {book.docx_name}")
        print(f"✔ PDF:  {book.pdf_name}")
        print(f"✔ Bilder: {len(figures)}")

    def _copy_if_exists(self, source, target):
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def build_docs():
    builder = DocumentationBuilder()
    builder.build_all()
