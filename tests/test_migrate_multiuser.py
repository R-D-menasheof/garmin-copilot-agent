"""Tests for the multi-user blob migration — TDD RED phase.

SAFETY CONTRACT (asserted by these tests):
- Migration COPIES global blobs into ``users/{owner_id}/`` scope.
- It NEVER deletes or moves originals — every source blob remains readable.
- It SKIPS the shared ``food_cache/`` (stays global) and anything already
  under ``users/``.
- Dry-run (the default) changes nothing.
- Re-running is idempotent and never clobbers an existing target.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from migrate_to_multiuser import migrate_blobs  # noqa: E402


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

        if self._name not in self._store:
            raise KeyError(self._name)
        return _DL(self._store[self._name])

    def upload_blob(self, data, overwrite: bool = False) -> None:
        if self._name in self._store and not overwrite:
            raise ValueError(f"blob exists: {self._name}")
        self._store[self._name] = data.encode() if isinstance(data, str) else data


class FakeBlob:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeContainer:
    """Minimal in-memory stand-in for an Azure ContainerClient."""

    def __init__(self, initial: dict[str, bytes] | None = None) -> None:
        self._store: dict[str, bytes] = dict(initial or {})

    def list_blobs(self, name_starts_with: str = ""):
        return [FakeBlob(n) for n in list(self._store) if n.startswith(name_starts_with)]

    def get_blob_client(self, name: str) -> FakeBlobClient:
        return FakeBlobClient(self._store, name)


def _seed() -> FakeContainer:
    return FakeContainer({
        "meals/2026-07-01.json": b'[{"food":"apple"}]',
        "goals/current.json": b'{"cal":2200}',
        "biometrics/2026-07-01.json": b'{"hr":60}',
        "summaries/latest.json": b'{"date":"2026-07-01"}',
        "medical/lab_trends.json": b'[{"metric":"LDL"}]',
        "food_cache/known_foods.json": b'[{"food_name":"cottage"}]',
    })


# ── Dry-run (default) ─────────────────────────────────────────────


class TestDryRun:
    def test_lists_all_user_blobs_to_copy(self) -> None:
        c = _seed()
        report = migrate_blobs(c, owner_id="roei", dry_run=True)
        srcs = {src for src, _ in report.to_copy}
        assert "meals/2026-07-01.json" in srcs
        assert "goals/current.json" in srcs
        assert "biometrics/2026-07-01.json" in srcs
        assert "summaries/latest.json" in srcs
        assert "medical/lab_trends.json" in srcs

    def test_excludes_food_cache(self) -> None:
        c = _seed()
        report = migrate_blobs(c, owner_id="roei", dry_run=True)
        srcs = {src for src, _ in report.to_copy}
        assert "food_cache/known_foods.json" not in srcs

    def test_targets_are_user_scoped(self) -> None:
        c = _seed()
        report = migrate_blobs(c, owner_id="roei", dry_run=True)
        mapping = dict(report.to_copy)
        assert mapping["meals/2026-07-01.json"] == "users/roei/meals/2026-07-01.json"

    def test_dry_run_writes_nothing(self) -> None:
        c = _seed()
        before = dict(c._store)
        migrate_blobs(c, owner_id="roei", dry_run=True)
        assert c._store == before  # unchanged
        assert not any(k.startswith("users/") for k in c._store)


# ── Real copy ─────────────────────────────────────────────────────


class TestCopy:
    def test_copies_each_blob_to_user_scope(self) -> None:
        c = _seed()
        migrate_blobs(c, owner_id="roei", dry_run=False)
        assert c._store["users/roei/meals/2026-07-01.json"] == b'[{"food":"apple"}]'
        assert c._store["users/roei/goals/current.json"] == b'{"cal":2200}'
        assert c._store["users/roei/medical/lab_trends.json"] == b'[{"metric":"LDL"}]'

    def test_originals_are_preserved(self) -> None:
        c = _seed()
        migrate_blobs(c, owner_id="roei", dry_run=False)
        # every original global blob STILL exists, untouched
        assert c._store["meals/2026-07-01.json"] == b'[{"food":"apple"}]'
        assert c._store["goals/current.json"] == b'{"cal":2200}'
        assert c._store["summaries/latest.json"] == b'{"date":"2026-07-01"}'

    def test_food_cache_left_at_global_path(self) -> None:
        c = _seed()
        migrate_blobs(c, owner_id="roei", dry_run=False)
        assert c._store["food_cache/known_foods.json"] == b'[{"food_name":"cottage"}]'
        assert "users/roei/food_cache/known_foods.json" not in c._store

    def test_verifies_copies(self) -> None:
        c = _seed()
        report = migrate_blobs(c, owner_id="roei", dry_run=False, verify=True)
        assert "users/roei/meals/2026-07-01.json" in report.verified
        assert not report.failed

    def test_reports_copied_count(self) -> None:
        c = _seed()
        report = migrate_blobs(c, owner_id="roei", dry_run=False)
        assert len(report.copied) == 5  # all but food_cache


# ── Idempotency / non-clobber ─────────────────────────────────────


class TestIdempotency:
    def test_skips_already_migrated_users_blobs(self) -> None:
        c = _seed()
        c._store["users/alice/meals/2026-01-01.json"] = b'{"x":1}'
        report = migrate_blobs(c, owner_id="roei", dry_run=True)
        srcs = {src for src, _ in report.to_copy}
        assert not any(s.startswith("users/") for s in srcs)

    def test_rerun_does_not_clobber_existing_target(self) -> None:
        c = _seed()
        migrate_blobs(c, owner_id="roei", dry_run=False)
        # simulate the app writing NEWER data to the user-scoped blob
        c._store["users/roei/goals/current.json"] = b'{"cal":1900}'
        report = migrate_blobs(c, owner_id="roei", dry_run=False)
        # the newer user-scoped value must be preserved, not overwritten
        assert c._store["users/roei/goals/current.json"] == b'{"cal":1900}'
        assert "users/roei/goals/current.json" in report.skipped_existing

    def test_rerun_copies_only_new_originals(self) -> None:
        c = _seed()
        migrate_blobs(c, owner_id="roei", dry_run=False)
        c._store["meals/2026-07-02.json"] = b'[{"food":"banana"}]'
        report = migrate_blobs(c, owner_id="roei", dry_run=False)
        copied = {src for src, _ in report.copied}
        assert copied == {"meals/2026-07-02.json"}
