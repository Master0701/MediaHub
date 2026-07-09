from pathlib import Path
import tempfile

from src.mediahub.docs.help_loader import HelpLoader
from src.mediahub.docs.manual_loader import (
    load_manual_text_entry,
    load_extra_manual_entries,
)


def test_load_manual_text_entry_missing_file_returns_none():
    with tempfile.TemporaryDirectory() as temp_dir:
        loader = HelpLoader(Path(temp_dir))

        entry = load_manual_text_entry(
            loader,
            "quick",
            "quick",
            "KURZANLEITUNG.txt",
        )

        assert entry is None


def test_load_manual_text_entry_reads_file():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        docs_dir = base_dir / "assets" / "docs" / "quick"
        docs_dir.mkdir(parents=True)

        file = docs_dir / "KURZANLEITUNG.txt"
        file.write_text("Das ist die Kurzanleitung.", encoding="utf-8")

        loader = HelpLoader(base_dir)

        entry = load_manual_text_entry(
            loader,
            "quick",
            "quick",
            "KURZANLEITUNG.txt",
        )

        assert entry is not None
        assert entry["title"] == "Kurzanleitung"
        assert entry["book"] == "quick"
        assert "kurzanleitung" in entry["keywords"]


def test_load_extra_manual_entries_reads_quick_and_developer():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)

        quick_dir = base_dir / "assets" / "docs" / "quick"
        dev_dir = base_dir / "assets" / "docs" / "developer"

        quick_dir.mkdir(parents=True)
        dev_dir.mkdir(parents=True)

        (quick_dir / "KURZANLEITUNG.txt").write_text(
            "Kurzanleitung Text",
            encoding="utf-8",
        )
        (dev_dir / "ENTWICKLERHANDBUCH.txt").write_text(
            "Entwicklerhandbuch Text",
            encoding="utf-8",
        )

        loader = HelpLoader(base_dir)
        entries = load_extra_manual_entries(loader)

        books = {entry["book"] for entry in entries}

        assert "quick" in books
        assert "developer" in books