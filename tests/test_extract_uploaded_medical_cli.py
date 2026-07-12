"""Tests for scripts/extract_uploaded_medical.py (Phase 6.3)."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from extract_uploaded_medical import download_pending_uploads, parse_args  # noqa: E402


class _Upload:
    def __init__(self, upload_id: str, filename: str, extracted: bool = False) -> None:
        self.id = upload_id
        self.filename = filename
        self.extracted = extracted


class _FakeStore:
    def __init__(self, uploads: list[_Upload], contents: dict[str, bytes]) -> None:
        self._uploads = uploads
        self._contents = contents
        self.marked: list[str] = []

    def load_medical_uploads(self) -> list[_Upload]:
        return self._uploads

    def load_medical_upload_content(self, upload_id: str) -> bytes | None:
        return self._contents.get(upload_id)

    def mark_medical_upload_extracted(self, upload_id: str) -> None:
        self.marked.append(upload_id)


class TestDownloadPendingUploads:
    def test_downloads_only_pending(self, tmp_path) -> None:
        store = _FakeStore(
            [_Upload("u1", "a.pdf"), _Upload("u2", "b.png", extracted=True)],
            {"u1": b"PDFDATA", "u2": b"PNGDATA"},
        )
        result = download_pending_uploads(store, tmp_path)

        assert len(result) == 1
        assert result[0]["id"] == "u1"
        assert (tmp_path / "u1_a.pdf").read_bytes() == b"PDFDATA"
        assert not (tmp_path / "u2_b.png").exists()

    def test_all_includes_extracted(self, tmp_path) -> None:
        store = _FakeStore(
            [_Upload("u2", "b.png", extracted=True)], {"u2": b"PNGDATA"}
        )
        result = download_pending_uploads(store, tmp_path, only_pending=False)

        assert len(result) == 1
        assert (tmp_path / "u2_b.png").read_bytes() == b"PNGDATA"

    def test_skips_missing_content(self, tmp_path) -> None:
        store = _FakeStore([_Upload("u1", "a.pdf")], {})  # no bytes available
        assert download_pending_uploads(store, tmp_path) == []


class TestParseArgs:
    def test_requires_user_id_and_flags(self) -> None:
        args = parse_args(["--user-id", "x", "--all"])
        assert args.user_id == "x"
        assert args.all is True

    def test_mark_extracted(self) -> None:
        args = parse_args(["--user-id", "x", "--mark-extracted", "u1"])
        assert args.mark_extracted == "u1"
