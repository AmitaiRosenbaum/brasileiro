from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import TestCase


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "rename_songs.py"
SRC_DIR = MODULE_PATH.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("rename_songs", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("rename_songs", module)
    spec.loader.exec_module(module)
    return module


rename_songs = load_module()


class RenameSongsTests(TestCase):
    def test_build_renamed_songs_normalizes_artist_order(self):
        split_files = [
            Path("001-first.pdf"),
            Path("002-second.pdf"),
        ]
        corrected_songs = [
            rename_songs.CorrectedSong(
                index=0,
                title="Olha Maria",
                artist="Antonio Carlos Jobim, Chico Buarque, Vinicius de Moraes",
            ),
            rename_songs.CorrectedSong(
                index=1,
                title="Olha Maria",
                artist="Chico Buarque, Vinicius de Moraes, Antonio Carlos Jobim",
            ),
        ]

        renamed_songs, warnings = rename_songs.build_renamed_songs(split_files, corrected_songs)

        self.assertEqual(warnings, [])
        self.assertEqual(
            [song.artist for song in renamed_songs],
            [
                "Antonio Carlos Jobim, Chico Buarque, Vinicius de Moraes",
                "Antonio Carlos Jobim, Chico Buarque, Vinicius de Moraes",
            ],
        )
        self.assertEqual([song.version for song in renamed_songs], [1, 2])
        self.assertEqual(
            [song.final_file for song in renamed_songs],
            [
                "olha-maria__antonio-carlos-jobim-chico-buarque-vinicius-de-moraes__v01.pdf",
                "olha-maria__antonio-carlos-jobim-chico-buarque-vinicius-de-moraes__v02.pdf",
            ],
        )
