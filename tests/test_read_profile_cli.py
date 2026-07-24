"""Tests for scripts/read_profile.py (Phase 6.2)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from read_profile import parse_args, read_profile  # noqa: E402


class TestParseArgs:
    def test_requires_user_id(self) -> None:
        args = parse_args(["--user-id", "u-123"])
        assert args.user_id == "u-123"

    def test_missing_user_id_exits(self) -> None:
        with pytest.raises(SystemExit):
            parse_args([])


class TestReadProfile:
    def test_returns_dump(self) -> None:
        blob = MagicMock()
        model = MagicMock()
        model.model_dump.return_value = {"display_name": "רועי"}
        blob.load_profile.return_value = model

        assert read_profile("u-123", store=blob) == {"display_name": "רועי"}

    def test_returns_none_when_absent(self) -> None:
        blob = MagicMock()
        blob.load_profile.return_value = None

        assert read_profile("u-123", store=blob) is None
