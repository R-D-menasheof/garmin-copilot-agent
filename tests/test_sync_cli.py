"""Tests for sync CLI — argument parsing and date resolution."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

# Import from scripts/sync.py — adjust path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync import parse_args, resolve_dates  # noqa: E402


class TestSyncCLI:
    def test_parse_days(self):
        args = parse_args(["--days", "7"])
        assert args.days == 7

    def test_parse_today(self):
        args = parse_args(["--today"])
        assert args.today is True

    def test_parse_from_to(self):
        args = parse_args(["--from", "2026-01-01", "--to", "2026-01-31"])
        assert args.start == date(2026, 1, 1)
        assert args.end == date(2026, 1, 31)

    def test_parse_from_without_to(self):
        args = parse_args(["--from", "2026-01-01"])
        assert args.start == date(2026, 1, 1)
        assert args.end is None  # resolve_dates will default to today

    def test_resolve_today(self):
        args = parse_args(["--today"])
        start, end = resolve_dates(args)
        today = date.today()
        assert start == today
        assert end == today

    def test_resolve_days(self):
        args = parse_args(["--days", "7"])
        start, end = resolve_dates(args)
        today = date.today()
        assert end == today
        assert start == today - timedelta(days=6)

    def test_resolve_from_to(self):
        args = parse_args(["--from", "2026-01-01", "--to", "2026-01-15"])
        start, end = resolve_dates(args)
        assert start == date(2026, 1, 1)
        assert end == date(2026, 1, 15)

    def test_resolve_from_defaults_to_today(self):
        args = parse_args(["--from", "2026-01-01"])
        start, end = resolve_dates(args)
        assert start == date(2026, 1, 1)
        assert end == date.today()

    def test_resolve_to_before_from_raises(self):
        args = parse_args(["--from", "2026-02-01", "--to", "2026-01-01"])
        with pytest.raises(ValueError, match="--to must not be before --from"):
            resolve_dates(args)

    def test_no_args_raises(self):
        with pytest.raises(SystemExit):
            parse_args([])
