from pathlib import Path

from src.mediahub.docs.models import DocBook


APP_NAME = "MediaHub"
APP_VERSION = "1.0.1"

ROOT = Path(__file__).resolve().parents[3]

SOURCE_DIR = ROOT / "docs_source"
APP_DOCS_DIR = ROOT / "assets" / "docs"
RELEASE_DOCS_DIR = ROOT / "release" / "docs"


BOOKS = [
    DocBook(
        key="quick",
        title="MediaHub Kurzanleitung",
        source_dir=SOURCE_DIR / "quick",
        image_dir=SOURCE_DIR / "quick" / "images",
        app_dir=APP_DOCS_DIR / "quick",
        release_dir=RELEASE_DOCS_DIR / "quick",
        txt_name="KURZANLEITUNG.txt",
        html_name="MediaHub_Kurzanleitung.html",
        pdf_name="MediaHub_Kurzanleitung.pdf",
        docx_name="MediaHub_Kurzanleitung.docx",
    ),
    DocBook(
        key="user",
        title="MediaHub Benutzerhandbuch",
        source_dir=SOURCE_DIR / "user",
        image_dir=SOURCE_DIR / "user" / "images",
        app_dir=APP_DOCS_DIR,
        release_dir=RELEASE_DOCS_DIR,
        txt_name="HANDBUCH.txt",
        html_name="MediaHub_Handbuch.html",
        pdf_name="MediaHub_Handbuch.pdf",
        docx_name="MediaHub_Handbuch.docx",
        index_name="help_index.json",
    ),
    DocBook(
        key="developer",
        title="MediaHub Entwicklerhandbuch",
        source_dir=SOURCE_DIR / "developer",
        image_dir=SOURCE_DIR / "developer" / "images",
        app_dir=APP_DOCS_DIR / "developer",
        release_dir=RELEASE_DOCS_DIR / "developer",
        txt_name="ENTWICKLERHANDBUCH.txt",
        html_name="MediaHub_Entwicklerhandbuch.html",
        pdf_name="MediaHub_Entwicklerhandbuch.pdf",
        docx_name="MediaHub_Entwicklerhandbuch.docx",
    ),
]