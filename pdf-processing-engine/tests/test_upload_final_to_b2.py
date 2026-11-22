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
                existence_check="head",
                prefix="prefix",
            )

        self.assertEqual([decision.action for decision in decisions], ["skip", "upload"])
        self.assertEqual(decisions[1].reason, "manifest is always rewritten with the merged catalog")

    def test_plan_uploads_defaults_to_listed_remote_keys(self):
        class FakePaginator:
            def paginate(self, **kwargs):
                self.kwargs = kwargs
                return [
                    {
                        "Contents": [
                            {"Key": "prefix/a__v01.pdf"},
                            {"Key": "prefix/unrelated.pdf"},
                        ]
                    }
                ]

        class FakeClient:
            def __init__(self):
                self.paginator = FakePaginator()

            def get_paginator(self, name):
                self.paginator_name = name
                return self.paginator

        client = FakeClient()
        existing_item = upload_final_to_b2.UploadItem(
            local_path=Path("/tmp/a.pdf"),
            remote_key="prefix/a__v01.pdf",
            content_type="application/pdf",
            item_type="pdf",
            local_file="a__v01.pdf",
        )
        new_item = upload_final_to_b2.UploadItem(
            local_path=Path("/tmp/b.pdf"),
            remote_key="prefix/b__v01.pdf",
            content_type="application/pdf",
            item_type="pdf",
            local_file="b__v01.pdf",
        )

        with patch.object(upload_final_to_b2, "remote_key_exists") as remote_key_exists:
            decisions = upload_final_to_b2.plan_uploads(
                client=client,
                bucket="bucket",
                items=[existing_item, new_item],
                overwrite=False,
                existence_check="list",
                prefix="prefix",
            )

        remote_key_exists.assert_not_called()
        self.assertEqual(client.paginator_name, "list_objects_v2")
        self.assertEqual(client.paginator.kwargs, {"Bucket": "bucket", "Prefix": "prefix/"})
        self.assertEqual([decision.action for decision in decisions], ["skip", "upload"])

    def test_plan_uploads_head_mode_checks_each_pdf_key(self):
        items = [
            upload_final_to_b2.UploadItem(
                local_path=Path("/tmp/a.pdf"),
                remote_key="prefix/a__v01.pdf",
                content_type="application/pdf",
                item_type="pdf",
                local_file="a__v01.pdf",
            ),
            upload_final_to_b2.UploadItem(
                local_path=Path("/tmp/b.pdf"),
                remote_key="prefix/b__v01.pdf",
                content_type="application/pdf",
                item_type="pdf",
                local_file="b__v01.pdf",
            ),
        ]

        with patch.object(
            upload_final_to_b2,
            "remote_key_exists",
            side_effect=[True, False],
        ) as remote_key_exists:
            decisions = upload_final_to_b2.plan_uploads(
                client=object(),
                bucket="bucket",
                items=items,
                overwrite=False,
                existence_check="head",
                prefix="prefix",
            )

        self.assertEqual(remote_key_exists.call_count, 2)
        self.assertEqual([decision.action for decision in decisions], ["skip", "upload"])

    def test_plan_uploads_list_mode_does_not_list_for_manifest_only(self):
        class FakeClient:
            def get_paginator(self, name):
                raise AssertionError("manifest-only plans should not list remote PDFs")

        manifest_item = upload_final_to_b2.build_manifest_upload_item(
            Path("/tmp/manifest.csv"),
            "manifest.csv",
            "prefix",
        )

        decisions = upload_final_to_b2.plan_uploads(
            client=FakeClient(),
            bucket="bucket",
            items=[manifest_item],
            overwrite=False,
            existence_check="list",
            prefix="prefix",
        )

        self.assertEqual([decision.action for decision in decisions], ["upload"])

    def test_build_manifest_upload_item_uses_manifest_name(self):
        item = upload_final_to_b2.build_manifest_upload_item(
            Path("/tmp/b2_merged_manifest.csv"),
            "manifest.csv",
            "prefix/inside",
        )

        self.assertEqual(item.remote_key, "prefix/inside/manifest.csv")
        self.assertEqual(item.item_type, "manifest")
        self.assertEqual(item.content_type, "text/csv")

    def test_adapt_local_versions_matches_remote_artist_reordering(self):
        remote_songs = [
            upload_final_to_b2.ManifestSong(
                index=0,
                source_file="remote.pdf",
                final_file="olha-maria__antonio-carlos-jobim-chico-buarque-vinicius-de-moraes__v01.pdf",
                title="Olha Maria",
                artist="Antonio Carlos Jobim, Chico Buarque, Vinicius de Moraes",
                version=1,
                song_key="olha-maria__antonio-carlos-jobim-chico-buarque-vinicius-de-moraes",
                title_slug="olha-maria",
                artist_slug="antonio-carlos-jobim-chico-buarque-vinicius-de-moraes",
            ),
        ]
        local_songs = [
            upload_final_to_b2.ManifestSong(
                index=1,
                source_file="local.pdf",
                final_file="placeholder.pdf",
                title="Olha Maria",
                artist="Chico Buarque, Vinicius de Moraes, Antonio Carlos Jobim",
                version=1,
                song_key="olha-maria__antonio-carlos-jobim-chico-buarque-vinicius-de-moraes",
                title_slug="olha-maria",
                artist_slug="antonio-carlos-jobim-chico-buarque-vinicius-de-moraes",
            ),
        ]

        adapted = upload_final_to_b2.adapt_local_versions(remote_songs, local_songs)

        self.assertEqual(adapted[0].version, 2)
        self.assertEqual(
            adapted[0].final_file,
            "olha-maria__antonio-carlos-jobim-chico-buarque-vinicius-de-moraes__v02.pdf",
        )

    def test_adapt_local_versions_appends_after_cloud_versions_when_manifest_is_stale(self):
        remote_songs = [
            upload_final_to_b2.ManifestSong(
                index=0,
                source_file="remote.pdf",
                final_file="olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes__v01.pdf",
                title="Olha Maria",
                artist="Tom Jobim, Chico Buarque, Vinicius de Moraes",
                version=1,
                song_key="olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes",
                title_slug="olha-maria",
                artist_slug="tom-jobim-chico-buarque-vinicius-de-moraes",
            ),
        ]
        local_songs = [
            upload_final_to_b2.ManifestSong(
                index=1,
                source_file="local.pdf",
                final_file="olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes__v01.pdf",
                title="Olha Maria",
                artist="Tom Jobim, Chico Buarque, Vinicius de Moraes",
                version=1,
                song_key="olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes",
                title_slug="olha-maria",
                artist_slug="tom-jobim-chico-buarque-vinicius-de-moraes",
            ),
        ]
        remote_keys = {
            "brasileiro-songs/olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes__v01.pdf",
            "brasileiro-songs/olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes__v02.pdf",
            "brasileiro-songs/olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes__v03.pdf",
            "brasileiro-songs/olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes__v04.pdf",
        }

        adapted = upload_final_to_b2.adapt_local_versions(
            remote_songs,
            local_songs,
            remote_keys=remote_keys,
        )

        self.assertEqual(adapted[0].version, 5)
        self.assertEqual(
            adapted[0].final_file,
            "olha-maria__tom-jobim-chico-buarque-vinicius-de-moraes__v05.pdf",
        )

    def test_attach_book_metadata_enriches_rows_without_rewriting_existing_metadata(self):
        songs = [
            upload_final_to_b2.ManifestSong(
                index=0,
                source_file="local.pdf",
                final_file="local__artist__v01.pdf",
                title="Local",
                artist="Artist",
                version=1,
                song_key="local__artist",
                title_slug="local",
                artist_slug="artist",
            ),
            upload_final_to_b2.ManifestSong(
                index=1,
                source_file="existing.pdf",
                final_file="existing__artist__v01.pdf",
                title="Existing",
                artist="Artist",
                book_title="Existing Book",
                book_song_index=9,
                version=1,
                song_key="existing__artist",
                title_slug="existing",
                artist_slug="artist",
            ),
        ]
        metadata = {
            "local.pdf": upload_final_to_b2.BookMetadata(
                book_title="Caetano Veloso II",
                book_song_index=3,
            ),
            "existing.pdf": upload_final_to_b2.BookMetadata(
                book_title="Caetano Veloso II",
                book_song_index=4,
            ),
        }

        enriched = upload_final_to_b2.attach_book_metadata(songs, metadata)

        self.assertEqual(enriched[0].book_title, "Caetano Veloso II")
        self.assertEqual(enriched[0].book_song_index, 3)
        self.assertEqual(enriched[1].book_title, "Existing Book")
        self.assertEqual(enriched[1].book_song_index, 9)
