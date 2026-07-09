from pathlib import Path
import json
import tempfile

from src.mediahub.docs.help_loader import HelpLoader


def test_help_loader_can_be_created():
    loader = HelpLoader(Path.cwd())

    assert loader is not None


def test_help_loader_candidate_dirs():
    loader = HelpLoader(Path.cwd())

    dirs = loader.candidate_dirs()

    assert isinstance(dirs, list)
    assert len(dirs) >= 1


def test_help_loader_loads_index():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        docs_dir = base_dir / "assets" / "docs"
        docs_dir.mkdir(parents=True)

        index = docs_dir / "help_index.json"
        index.write_text(
            json.dumps(
                [
                    {
                        "book": "user",
                        "title": "Testhilfe",
                        "key": "test",
                        "keywords": "test hilfe",
                        "text": "Das ist ein Test.",
                        "source": "test.md",
                    }
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        loader = HelpLoader(base_dir)
        data = loader.load()

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Testhilfe"


def test_help_loader_missing_index_returns_empty_list():
    with tempfile.TemporaryDirectory() as temp_dir:
        loader = HelpLoader(Path(temp_dir))

        data = loader.load()

        assert data == []


def test_help_loader_first_existing_doc():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        docs_dir = base_dir / "assets" / "docs"
        docs_dir.mkdir(parents=True)

        doc = docs_dir / "HANDBUCH.txt"
        doc.write_text("Test-Handbuch", encoding="utf-8")

        loader = HelpLoader(base_dir)
        found = loader.first_existing_doc("HANDBUCH.txt")

        assert found == doc