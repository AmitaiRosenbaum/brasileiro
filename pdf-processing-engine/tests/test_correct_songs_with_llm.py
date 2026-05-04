from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import TestCase


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "correct_songs_with_llm.py"
SRC_DIR = MODULE_PATH.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("correct_songs_with_llm", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("correct_songs_with_llm", module)
    spec.loader.exec_module(module)
    return module


correct_songs_with_llm = load_module()


class CorrectSongsWithLlmTests(TestCase):
    def test_apply_artist_alias_map_canonicalizes_and_sorts_artists(self):
        songs = [
            {
                "title": "Olha Maria",
                "artist": "Tom Jobim, Vinicius de Moraes, Chico Buarque",
            }
        ]
        artist_alias_map = {
            "Tom Jobim": "Antônio Carlos Jobim",
            "Vinicius de Moraes": "Vinicius de Moraes",
            "Chico Buarque": "Chico Buarque",
        }

        normalized = correct_songs_with_llm.apply_artist_alias_map(songs, artist_alias_map)

        self.assertEqual(
            normalized,
            [
                {
                    "title": "Olha Maria",
                    "artist": "Antônio Carlos Jobim, Chico Buarque, Vinicius de Moraes",
                }
            ],
        )

    def test_apply_title_alias_map_canonicalizes_titles(self):
        songs = [
            {
                "title": "Amor em paz",
                "artist": "Antônio Carlos Jobim, Vinicius de Moraes",
            },
            {
                "title": "Ana Lu'iza",
                "artist": "Tom Jobim",
            },
        ]
        title_alias_map = {
            ("Amor em paz", "Antônio Carlos Jobim, Vinicius de Moraes"): "Amor em Paz",
            ("Ana Lu'iza", "Tom Jobim"): "Ana Luiza",
        }

        normalized = correct_songs_with_llm.apply_title_alias_map(songs, title_alias_map)

        self.assertEqual(
            normalized,
            [
                {
                    "title": "Amor em Paz",
                    "artist": "Antônio Carlos Jobim, Vinicius de Moraes",
                },
                {
                    "title": "Ana Luiza",
                    "artist": "Tom Jobim",
                },
            ],
        )
