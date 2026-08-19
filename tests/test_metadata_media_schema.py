from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MIGRATION = (
    ROOT / "src" / "mediahub" / "storage" / "migration.py"
).read_text(encoding="utf-8")

REPOSITORY = (
    ROOT / "src" / "mediahub" / "storage" / "repository.py"
).read_text(encoding="utf-8")

MAIN_WINDOW = (
    ROOT / "src" / "mediahub" / "gui" / "main_window.py"
).read_text(encoding="utf-8")


def test_video_table_has_movie_and_series_metadata_columns():
    expected = {
        "\"media_type\", \"TEXT NOT NULL DEFAULT 'video'\"",
        "\"year\", \"INTEGER NOT NULL DEFAULT 0\"",
        "\"series\", \"TEXT NOT NULL DEFAULT ''\"",
        "\"season\", \"INTEGER NOT NULL DEFAULT 0\"",
        "\"episode\", \"INTEGER NOT NULL DEFAULT 0\"",
        "\"episode_title\", \"TEXT NOT NULL DEFAULT ''\"",
    }
    for snippet in expected:
        assert snippet in MIGRATION


def test_repository_allows_shared_movie_and_series_metadata():
    for field in (
        "media_type",
        "title",
        "description",
        "year",
        "series",
        "season",
        "episode",
        "episode_title",
        "upload_date",
    ):
        assert f'\"{field}\"' in REPOSITORY


def test_metadata_update_maps_movie_and_series_fields():
    for mapping in (
        '\"media_type\": \"media_type\"',
        '\"year\": \"year\"',
        '\"series\": \"series\"',
        '\"season\": \"season\"',
        '\"episode\": \"episode\"',
        '\"episode_title\": \"episode_title\"',
    ):
        assert mapping in MAIN_WINDOW

    unsupported_block = MAIN_WINDOW.split(
        "unsupported_editor_fields = {", 1
    )[1].split("}", 1)[0]

    assert '\"year\"' not in unsupported_block
    assert '\"series\"' not in unsupported_block
    assert '\"season\"' not in unsupported_block
    assert '\"episode\"' not in unsupported_block
    assert '\"channel\"' in unsupported_block
    assert '\"playlist\"' in unsupported_block
