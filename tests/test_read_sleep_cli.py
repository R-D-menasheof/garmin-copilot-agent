from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from read_sleep import parse_args, read_sleep_direct  # noqa: E402


def test_parses_user_id() -> None:
    assert parse_args(["--user-id", "u-123"]).user_id == "u-123"


def test_reads_sleep_entries_from_user_store() -> None:
    store = MagicMock()
    entry = MagicMock()
    entry.model_dump.return_value = {"date": "2026-07-10"}
    store.load_sleep_entries.return_value = [entry]
    start = date(2026, 7, 4)
    end = date(2026, 7, 10)

    assert read_sleep_direct("u-123", start, end, store=store) == [
        {"date": "2026-07-10"}
    ]
    store.load_sleep_entries.assert_called_once_with(start, end)
