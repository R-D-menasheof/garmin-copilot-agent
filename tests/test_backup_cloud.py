"""Tests for the cloud blob backup — TDD RED phase.

The backup downloads every blob to a local folder before any migration, as an
extra safety net. It is read-only against the cloud (download only).
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from backup_cloud import backup_container  # noqa: E402


class FakeBlobClient:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name

    def download_blob(self):
        class _DL:
            def __init__(self, data: bytes) -> None:
                self._data = data

            def readall(self) -> bytes:
                return self._data

        return _DL(self._store[self._name])


class FakeBlob:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeContainer:
    def __init__(self, initial: dict[str, bytes]) -> None:
        self._store = dict(initial)

    def list_blobs(self, name_starts_with: str = ""):
        return [FakeBlob(n) for n in self._store if n.startswith(name_starts_with)]

    def get_blob_client(self, name: str) -> FakeBlobClient:
        return FakeBlobClient(self._store, name)


def _seed() -> FakeContainer:
    return FakeContainer({
        "meals/2026-07-01.json": b'[{"food":"apple"}]',
        "medical/lab_trends.json": b'[{"metric":"LDL"}]',
        "food_cache/known_foods.json": b'[{"food_name":"cottage"}]',
        "nested/deep/path.json": b'{"x":1}',
    })


class TestBackup:
    def test_downloads_every_blob_preserving_path(self, tmp_path) -> None:
        c = _seed()
        report = backup_container(c, tmp_path)

        assert (tmp_path / "meals" / "2026-07-01.json").read_bytes() == b'[{"food":"apple"}]'
        assert (tmp_path / "medical" / "lab_trends.json").exists()
        assert (tmp_path / "food_cache" / "known_foods.json").exists()
        assert (tmp_path / "nested" / "deep" / "path.json").read_bytes() == b'{"x":1}'
        assert report.count == 4

    def test_reports_downloaded_names(self, tmp_path) -> None:
        c = _seed()
        report = backup_container(c, tmp_path)
        assert "meals/2026-07-01.json" in report.names
        assert "food_cache/known_foods.json" in report.names

    def test_creates_destination_dir(self, tmp_path) -> None:
        c = _seed()
        dest = tmp_path / "does-not-exist-yet"
        backup_container(c, dest)
        assert dest.is_dir()

    def test_does_not_mutate_cloud(self, tmp_path) -> None:
        c = _seed()
        before = dict(c._store)
        backup_container(c, tmp_path)
        assert c._store == before  # download-only, cloud untouched
