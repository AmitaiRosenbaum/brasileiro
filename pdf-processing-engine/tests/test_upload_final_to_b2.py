from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "scripts"
    / "cloud"
    / "upload_final_to_b2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("upload_final_to_b2", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("upload_final_to_b2", module)
    spec.loader.exec_module(module)
    return module


fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = lambda *args, **kwargs: None
sys.modules.setdefault("boto3", fake_boto3)

fake_botocore = types.ModuleType("botocore")
fake_config = types.ModuleType("botocore.config")


class FakeConfig:
    def __init__(self, *args, **kwargs):
        pass


fake_config.Config = FakeConfig
fake_botocore.config = fake_config
sys.modules.setdefault("botocore", fake_botocore)
sys.modules.setdefault("botocore.config", fake_config)


upload_final_to_b2 = load_module()


class UploadFinalToB2Tests(TestCase):
    def test_reindex_manifest_songs_replaces_sparse_indices(self):
        songs = [
            upload_final_to_b2.ManifestSong(
                index=17,
                source_file="a.pdf",
                final_file="a__v01.pdf",
                title="A",
                artist="Artist",
                version=1,
                song_key="a",
                title_slug="a",
                artist_slug="artist",
            ),
            upload_final_to_b2.ManifestSong(
                index=91,
                source_file="b.pdf",
                final_file="b__v01.pdf",
                title="B",
                artist="Artist",
                version=1,
                song_key="b",
                title_slug="b",
                artist_slug="artist",
            ),
        ]

        reindexed = upload_final_to_b2.reindex_manifest_songs(songs)

        self.assertEqual([song.index for song in reindexed], [0, 1])
        self.assertEqual([song.final_file for song in reindexed], ["a__v01.pdf", "b__v01.pdf"])

    def test_plan_uploads_always_uploads_manifest(self):
        pdf_item = upload_final_to_b2.UploadItem(
            local_path=Path("/tmp/a.pdf"),
            remote_key="prefix/a__v01.pdf",
            content_type="application/pdf",
            item_type="pdf",
            local_file="a__v01.pdf",
        )
        manifest_item = upload_final_to_b2.build_manifest_upload_item(
            Path("/tmp/manifest.csv"),
            "manifest.csv",
            "prefix",
        )

        def fake_remote_key_exists(client, bucket, key):
            if key == manifest_item.remote_key:
                raise AssertionError("manifest existence should not be checked")
            return True

        with patch.object(
            upload_final_to_b2,
            "remote_key_exists",
            side_effect=fake_remote_key_exists,
        ):
            decisions = upload_final_to_b2.plan_uploads(
                client=object(),
                bucket="bucket",
                items=[pdf_item, manifest_item],
                overwrite=False,
            )

        self.assertEqual([decision.action for decision in decisions], ["skip", "upload"])
        self.assertEqual(decisions[1].reason, "manifest is always rewritten with the merged catalog")

    def test_build_manifest_upload_item_uses_manifest_name(self):
        item = upload_final_to_b2.build_manifest_upload_item(
            Path("/tmp/b2_merged_manifest.csv"),
            "manifest.csv",
            "prefix/inside",
        )

        self.assertEqual(item.remote_key, "prefix/inside/manifest.csv")
        self.assertEqual(item.item_type, "manifest")
        self.assertEqual(item.content_type, "text/csv")
