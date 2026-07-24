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

from set_goals import parse_args, send_goals, save_goals_direct


class TestParseArgs:
    def test_parses_macro_args(self) -> None:
        args = parse_args([
            "--calories", "1800",
            "--protein", "120",
            "--carbs", "195",
            "--fat", "60",
            "--weight", "80",
            "--tdee", "2400",
            "--calculation-method", "mifflin_st_jeor+garmin",
        ])
        assert args.calories == 1800
        assert args.protein == 120.0
        assert args.carbs == 195.0
        assert args.fat == 60.0
        assert args.weight == 80.0
        assert args.tdee == 2400
        assert args.calculation_method == "mifflin_st_jeor+garmin"
        assert args.calculation_version == 1

    def test_missing_calories_exits_error(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--protein", "180"])

    def test_missing_calculation_provenance_exits_error(self) -> None:
        with pytest.raises(SystemExit):
            parse_args([
                "--calories", "1800",
                "--protein", "120",
                "--carbs", "195",
                "--fat", "60",
            ])


class TestSendGoals:
    @patch("set_goals.httpx")
    def test_sends_correct_payload(self, mock_httpx) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_httpx.post.return_value = mock_resp

        result = send_goals(
            calories=1800,
            protein=120.0,
            carbs=195.0,
            fat=60.0,
            calculated_from_weight_kg=80.0,
            estimated_tdee_kcal=2400,
            calculation_method="mifflin_st_jeor+garmin",
            api_url="http://localhost:7071/api",
            api_key="test-key",
        )

        assert result["status"] == "ok"
        call_args = mock_httpx.post.call_args
        body = json.loads(call_args.kwargs.get("content") or call_args[1].get("content"))
        assert body["calories_target"] == 1800
        assert body["protein_g_target"] == 120.0
        assert body["calculated_from_weight_kg"] == 80.0
        assert body["estimated_tdee_kcal"] == 2400
        assert body["calculation_method"] == "mifflin_st_jeor+garmin"
        assert body["calculation_version"] == 1

    @patch("set_goals.httpx")
    def test_api_error_raises(self, mock_httpx) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("Server Error")
        mock_httpx.post.return_value = mock_resp

        with pytest.raises(Exception, match="Server Error"):
            send_goals(
                calories=1800,
                protein=120.0,
                carbs=195.0,
                fat=60.0,
                calculated_from_weight_kg=80.0,
                estimated_tdee_kcal=2400,
                calculation_method="mifflin_st_jeor+garmin",
                api_url="http://localhost:7071/api",
                api_key="test-key",
            )

    def test_rejects_macro_calorie_mismatch(self) -> None:
        with pytest.raises(ValueError, match="macro calories"):
            send_goals(
                calories=2200,
                protein=180.0,
                carbs=250.0,
                fat=70.0,
                calculated_from_weight_kg=80.0,
                estimated_tdee_kcal=2400,
                calculation_method="mifflin_st_jeor+garmin",
            )


class TestSaveGoalsDirect:
    def test_parses_user_id(self) -> None:
        args = parse_args([
            "--calories", "1800", "--protein", "120",
            "--carbs", "195", "--fat", "60", "--user-id", "u-123",
            "--weight", "80", "--tdee", "2400",
            "--calculation-method", "mifflin_st_jeor+garmin",
        ])
        assert args.user_id == "u-123"

    def test_saves_to_user_store(self) -> None:
        blob = MagicMock()

        result = save_goals_direct(
            "u-123",
            1800,
            120.0,
            195.0,
            60.0,
            calculated_from_weight_kg=80.0,
            estimated_tdee_kcal=2400,
            calculation_method="mifflin_st_jeor+garmin",
            store=blob,
        )

        assert result["status"] == "ok"
        assert result["user_id"] == "u-123"
        blob.save_goals.assert_called_once()
        goal = blob.save_goals.call_args.args[0]
        assert goal.calories_target == 1800
        assert goal.protein_g_target == 120.0
        assert goal.set_by == "agent"
        assert goal.calculated_from_weight_kg == 80.0
        assert goal.estimated_tdee_kcal == 2400
