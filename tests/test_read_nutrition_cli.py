"""Tests for scripts/read_nutrition.py CLI.

TDD RED phase. HTTP calls mocked.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure scripts are importable
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "scripts"))

from read_nutrition import parse_args, resolve_dates, fetch_combined


class TestParseArgs:
    def test_parses_date_args(self) -> None:
        args = parse_args(["--from", "2026-03-28", "--to", "2026-04-04"])
        assert args.start == date(2026, 3, 28)
        assert args.end == date(2026, 4, 4)

    def test_default_last_7_days(self) -> None:
        args = parse_args([])
        start, end = resolve_dates(args)
        expected_end = date.today()
        expected_start = expected_end - timedelta(days=6)
        assert start == expected_start
        assert end == expected_end


class TestFetchCombined:
    @patch("read_nutrition.httpx")
    def test_outputs_json(self, mock_httpx) -> None:
        payload = {
            "nutrition": {"2026-04-04": [{"food_name": "banana", "calories": 89}]},
            "biometrics": {"2026-04-04": {"steps": 8500}},
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_resp

        result = fetch_combined(
            date(2026, 4, 4), date(2026, 4, 4),
            api_url="http://localhost:7071/api",
            api_key="test-key",
        )

        assert result == payload
        mock_httpx.get.assert_called_once()

    @patch("read_nutrition.httpx")
    def test_api_error_raises(self, mock_httpx) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("Server Error")
        mock_httpx.get.return_value = mock_resp

        with pytest.raises(Exception, match="Server Error"):
            fetch_combined(
                date(2026, 4, 4), date(2026, 4, 4),
                api_url="http://localhost:7071/api",
                api_key="test-key",
            )
