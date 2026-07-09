from pathlib import Path
import tempfile

from src.mediahub.docs.screenshot_catalog import (
    USER_SCREENSHOTS,
    scan_screenshots,
    missing_screenshots,
)


def test_user_screenshots_catalog_is_not_empty():
    assert isinstance(USER_SCREENSHOTS, list)
    assert len(USER_SCREENSHOTS) > 0


def test_scan_screenshots_detects_existing_and_missing_files():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        image_dir = base_dir / "docs_source" / "user" / "images"
        image_dir.mkdir(parents=True)

        first = USER_SCREENSHOTS[0]
        (image_dir / first["filename"]).write_text("test", encoding="utf-8")

        result = scan_screenshots(base_dir)

        assert isinstance(result, list)
        assert len(result) == len(USER_SCREENSHOTS)

        found_first = [item for item in result if item["filename"] == first["filename"]][0]

        assert found_first["exists"] is True
        assert found_first["path"].endswith(first["filename"])


def test_missing_screenshots_returns_only_missing_items():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)

        missing = missing_screenshots(base_dir)

        assert isinstance(missing, list)
        assert len(missing) == len(USER_SCREENSHOTS)

        for item in missing:
            assert item["exists"] is False