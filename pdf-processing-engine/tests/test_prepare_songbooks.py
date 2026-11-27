import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from prepare_songbooks import (  # noqa: E402
    BookConfig,
    EXCLUDED_PAGE,
    TITLE_PAGE,
    SongBoundary,
    build_boundaries,
    repeated_text_ratio,
    safe_filename,
    validate_manual_start_pages,
)


class PrepareSongbooksTests(unittest.TestCase):
    def test_book_config_accepts_reviewed_manual_boundaries(self):
        config = BookConfig(
            name="book",
            title="Book",
            manual_start_pages=[3, 5],
            page_overrides={"3": {"title": "First song"}},
        )

        self.assertEqual(config.manual_start_pages, [3, 5])
        self.assertEqual(config.page_overrides["3"]["title"], "First song")

    def test_build_boundaries_starts_at_titles_and_stops_at_excluded_pages(self):
        labels = [1, TITLE_PAGE, 1, TITLE_PAGE, 1, EXCLUDED_PAGE, 1, TITLE_PAGE, 1]

        self.assertEqual(
            build_boundaries(labels),
            [
                SongBoundary(song_index=1, start_index=1, end_index=3),
                SongBoundary(song_index=2, start_index=3, end_index=5),
                SongBoundary(song_index=3, start_index=7, end_index=9),
            ],
        )

    def test_reviewed_boundaries_must_be_unique_sorted_and_complete(self):
        with self.assertRaisesRegex(ValueError, "unique and ascending"):
            validate_manual_start_pages(
                BookConfig(
                    name="book",
                    title="Book",
                    expected_song_count=2,
                    manual_start_pages=[5, 3],
                ),
                10,
            )

    def test_reviewed_start_cannot_also_be_excluded(self):
        with self.assertRaisesRegex(ValueError, "both song starts and excluded"):
            validate_manual_start_pages(
                BookConfig(
                    name="book",
                    title="Book",
                    expected_song_count=2,
                    manual_start_pages=[3, 5],
                    excluded_pages=[5],
                ),
                10,
            )

    def test_reviewed_titles_must_match_reviewed_starts(self):
        with self.assertRaisesRegex(ValueError, "reviewed titles"):
            validate_manual_start_pages(
                BookConfig(
                    name="book",
                    title="Book",
                    expected_song_count=2,
                    manual_start_pages=[3, 5],
                    reviewed_titles=["Only one title"],
                ),
                10,
            )
        with self.assertRaisesRegex(ValueError, "expects 3 songs"):
            validate_manual_start_pages(
                BookConfig(
                    name="book",
                    title="Book",
                    expected_song_count=3,
                    manual_start_pages=[3, 5],
                ),
                10,
            )

    def test_build_boundaries_returns_empty_when_no_title_exists(self):
        self.assertEqual(build_boundaries([1, 1, EXCLUDED_PAGE]), [])

    def test_safe_filename_removes_path_and_shell_punctuation(self):
        self.assertEqual(safe_filename('  A/B: Canção?  ', 'fallback'), 'AB Canção')
        self.assertEqual(safe_filename('///', 'fallback'), 'fallback')

    def test_repeated_text_ratio_detects_bogus_repeated_text_layers(self):
        self.assertEqual(repeated_text_ratio(["same watermark"] * 3), 0.0)
        self.assertEqual(repeated_text_ratio(["same watermark text layer"] * 3), 1.0)
        self.assertEqual(
            repeated_text_ratio(
                [
                    "same watermark text layer",
                    "same watermark text layer",
                    "a different real song text layer",
                ]
            ),
            2 / 3,
        )


if __name__ == "__main__":
    unittest.main()
