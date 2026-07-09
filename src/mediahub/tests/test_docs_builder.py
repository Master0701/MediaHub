from __future__ import annotations

import importlib
from pathlib import Path

from src.mediahub.tests.test_report import TestResult


EXPECTED_BUILDER_FILES = [
    "src/mediahub/docs/builder.py",
    "src/mediahub/docs/config.py",
    "src/mediahub/docs/parser.py",
    "src/mediahub/docs/txt_exporter.py",
    "src/mediahub/docs/html_exporter.py",
    "src/mediahub/docs/docx_exporter.py",
    "src/mediahub/docs/pdf_exporter.py",
    "src/mediahub/docs/help_index_exporter.py",
    "build_docs.py",
]

EXPECTED_DOC_OUTPUTS = [
    "assets/docs/quick/KURZANLEITUNG.txt",
    "assets/docs/quick/MediaHub_Kurzanleitung.html",
    "assets/docs/quick/MediaHub_Kurzanleitung.docx",
    "assets/docs/quick/MediaHub_Kurzanleitung.pdf",
    "assets/docs/HANDBUCH.txt",
    "assets/docs/MediaHub_Handbuch.html",
    "assets/docs/MediaHub_Handbuch.docx",
    "assets/docs/MediaHub_Handbuch.pdf",
    "assets/docs/help_index.json",
    "assets/docs/developer/ENTWICKLERHANDBUCH.txt",
    "assets/docs/developer/MediaHub_Entwicklerhandbuch.html",
    "assets/docs/developer/MediaHub_Entwicklerhandbuch.docx",
    "assets/docs/developer/MediaHub_Entwicklerhandbuch.pdf",
]


def run_tests(base_dir: Path, mode: str):
    results: list[TestResult] = []
    base_dir = Path(base_dir)

    for rel_path in EXPECTED_BUILDER_FILES:
        path = base_dir / rel_path
        results.append(
            TestResult(
                "Doku-Builder",
                rel_path,
                "OK" if path.exists() else "ERROR",
                "vorhanden" if path.exists() else "fehlt",
            )
        )

    _test_builder_import(results)
    _test_build_docs_entrypoint(base_dir, results)
    _test_docs_source(base_dir, results)
    _test_generated_outputs(base_dir, results)

    if mode.lower() in {"full", "release"}:
        _test_parser_reads_books(results)

    return results


def _test_builder_import(results: list[TestResult]) -> None:
    try:
        module = importlib.import_module("src.mediahub.docs.builder")
        builder_class = getattr(module, "DocumentationBuilder", None)
        build_docs = getattr(module, "build_docs", None)
        ok = builder_class is not None and callable(build_docs)
        results.append(
            TestResult(
                "Doku-Builder",
                "Builder-Import",
                "OK" if ok else "ERROR",
                "DocumentationBuilder und build_docs importierbar" if ok else "Import unvollständig",
            )
        )
    except Exception as exc:
        results.append(TestResult("Doku-Builder", "Builder-Import", "ERROR", f"Import fehlgeschlagen: {exc}"))


def _test_build_docs_entrypoint(base_dir: Path, results: list[TestResult]) -> None:
    path = base_dir / "build_docs.py"
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8", errors="ignore")
    uses_builder = "from src.mediahub.docs.builder import build_docs" in text
    is_small = len(text.splitlines()) <= 15

    status = "OK" if uses_builder and is_small else "ERROR"
    message = "kleiner Starter nutzt Doku-Builder" if status == "OK" else "Starter ist noch zu groß oder nutzt Builder nicht"
    results.append(TestResult("Doku-Builder", "build_docs.py Starter", status, message))


def _test_docs_source(base_dir: Path, results: list[TestResult]) -> None:
    source_root = base_dir / "docs_source"
    for section in ["quick", "user", "developer"]:
        folder = source_root / section
        md_files = sorted(folder.glob("*.md")) if folder.exists() else []
        status = "OK" if md_files else "ERROR"
        message = f"{len(md_files)} Markdown-Dateien" if md_files else "keine Markdown-Dateien gefunden"
        results.append(TestResult("Doku-Builder", f"docs_source/{section}", status, message))


def _test_generated_outputs(base_dir: Path, results: list[TestResult]) -> None:
    missing = []
    for rel_path in EXPECTED_DOC_OUTPUTS:
        if not (base_dir / rel_path).exists():
            missing.append(rel_path)

    if missing:
        results.append(
            TestResult(
                "Doku-Builder",
                "generierte Dokumente",
                "WARN",
                f"{len(missing)} Ausgaben fehlen",
                "\n".join(missing),
            )
        )
    else:
        results.append(TestResult("Doku-Builder", "generierte Dokumente", "OK", "alle Standard-Ausgaben vorhanden"))


def _test_parser_reads_books(results: list[TestResult]) -> None:
    try:
        from src.mediahub.docs.config import BOOKS
        from src.mediahub.docs.parser import MarkdownParser

        parser = MarkdownParser()
        for book in BOOKS:
            docs = parser.read_docs(book)
            status = "OK" if docs else "ERROR"
            message = f"{len(docs)} Kapitel lesbar" if docs else "keine Kapitel lesbar"
            results.append(TestResult("Doku-Builder", f"Parser {book.key}", status, message))
    except Exception as exc:
        results.append(TestResult("Doku-Builder", "Parser-Test", "ERROR", f"Parser-Test fehlgeschlagen: {exc}"))
