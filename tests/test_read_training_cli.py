from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from read_training import parse_args, read_training_direct  # noqa: E402


def test_parses_user_id() -> None:
    assert parse_args(["--user-id", "u-123"]).user_id == "u-123"


def test_reads_training_from_user_store() -> None:
    store = MagicMock()
    program = MagicMock()
    program.model_dump.return_value = {"id": "training-1"}
    store.load_active_training_program.return_value = program

    assert read_training_direct("u-123", store=store) == {"id": "training-1"}
    store.load_active_training_program.assert_called_once_with()


def test_returns_none_without_active_training() -> None:
    store = MagicMock()
    store.load_active_training_program.return_value = None

    assert read_training_direct("u-123", store=store) is None
