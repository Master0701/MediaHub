from pathlib import Path
import tempfile

from src.mediahub.docs.screenshot_catalog import USER_SCREENSHOTS
from src.mediahub.docs.screenshot_report import build_screenshot_report


def test_screenshot_report_contains_summary():
    with tempfile.TemporaryDirectory() as temp_dir:
        report = build_screenshot_report(Path(temp_dir))

        assert "MediaHub Screenshot-Bericht" in report
        assert "Vorhanden:" in report
        assert "Fehlend:" in report


def test_screenshot_report_detects_existing_file():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        image_dir = base_dir / "docs_source" / "user" / "images"
        image_dir.mkdir(parents=True)

        first = USER_SCREENSHOTS[0]
        (image_dir / first["filename"]).write_text("test", encoding="utf-8")

        report = build_screenshot_report(base_dir)

        assert first["filename"] in report
        assert "✅" in report
        assert "⚠" in report