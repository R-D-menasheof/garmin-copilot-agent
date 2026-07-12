from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from read_goals import parse_args, read_goals_direct  # noqa: E402


def test_parses_user_id() -> None:
    assert parse_args(["--user-id", "u-123"]).user_id == "u-123"


def test_reads_goal_programs_from_user_store() -> None:
    store = MagicMock()
    program = MagicMock()
    program.model_dump.return_value = {"id": "goal-1"}
    store.load_goal_programs.return_value = [program]

    assert read_goals_direct("u-123", store=store) == [{"id": "goal-1"}]
    store.load_goal_programs.assert_called_once_with()
