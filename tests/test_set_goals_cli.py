"""Tests for scripts/set_goals.py CLI.

TDD RED phase. HTTP calls mocked.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from set_goals import parse_args, send_goals


class TestParseArgs:
    def test_parses_macro_args(self) -> None:
        args = parse_args([
            "--calories", "2200",
            "--protein", "180",
            "--carbs", "250",
            "--fat", "70",
        ])
        assert args.calories == 2200
        assert args.protein == 180.0
        assert args.carbs == 250.0
        assert args.fat == 70.0

    def test_missing_calories_exits_error(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--protein", "180"])


class TestSendGoals:
    @patch("set_goals.httpx")
    def test_sends_correct_payload(self, mock_httpx) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_httpx.post.return_value = mock_resp

        result = send_goals(
            calories=2200, protein=180.0, carbs=250.0, fat=70.0,
            api_url="http://localhost:7071/api",
            api_key="test-key",
        )

        assert result["status"] == "ok"
        call_args = mock_httpx.post.call_args
        body = json.loads(call_args.kwargs.get("content") or call_args[1].get("content"))
        assert body["calories_target"] == 2200
        assert body["protein_g_target"] == 180.0

    @patch("set_goals.httpx")
    def test_api_error_raises(self, mock_httpx) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("Server Error")
        mock_httpx.post.return_value = mock_resp

        with pytest.raises(Exception, match="Server Error"):
            send_goals(
                calories=2200, protein=180.0, carbs=250.0, fat=70.0,
                api_url="http://localhost:7071/api",
                api_key="test-key",
            )
