"""One-time script to seed real data: goal program + lab trends."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

import httpx

API_URL = os.environ.get("VITALIS_API_URL", "https://func-vitalis-api.azurewebsites.net/api")
API_KEY = os.environ.get("VITALIS_API_KEY", "PdVicIlE5QN27FwSk6rOjbvZMLzhpC1s")
HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}


def seed_goal_program() -> None:
    """Seed the 'Project 100kg' goal program."""
    program = {
        "name_he": 'פרויקט 100 ק"ג',
        "description_he": "ירידה מ-112 ל-100 ק\"ג — שילוב שחייה + תזונה + שינה",
        "duration_weeks": 16,
        "milestones": [
            {"title_he": "שקילה שבועית קבועה", "target_metric": "weekly_weighins", "target_value": 1, "current_value": 0},
            {"title_he": "שינה 7+ שעות (5/7 לילות)", "target_metric": "nights_above_7h", "target_value": 5, "current_value": 1},
            {"title_he": "שחייה 3x/שבוע", "target_metric": "weekly_swims", "target_value": 3, "current_value": 2.5},
            {"title_he": 'משקל 108 ק"ג', "target_metric": "weight_kg", "target_value": 108, "current_value": 112},
            {"title_he": 'משקל 104 ק"ג', "target_metric": "weight_kg", "target_value": 104, "current_value": 112},
            {"title_he": 'משקל 100 ק"ג', "target_metric": "weight_kg", "target_value": 100, "current_value": 112},
        ],
        "progress_pct": 8,
    }
    r = httpx.post(f"{API_URL}/v1/goals/programs", headers=HEADERS,
                   content=json.dumps(program, ensure_ascii=False))
    print(f"Goal program: {r.status_code}")


def seed_lab_trends() -> None:
    """Seed real lab trends from Sep 2022 and Sep 2025 blood tests."""
    trends = [
        {
            "metric": "LDL",
            "display_name_he": "כולסטרול LDL",
            "values": [
                {"date": "2022-09-01", "value": 99, "unit": "mg/dL", "reference_range": "<130", "status": "normal"},
                {"date": "2025-09-03", "value": 116.4, "unit": "mg/dL", "reference_range": "<130", "status": "normal"},
            ],
        },
        {
            "metric": "HDL",
            "display_name_he": "כולסטרול HDL",
            "values": [
                {"date": "2022-09-01", "value": 44, "unit": "mg/dL", "reference_range": ">40", "status": "normal"},
                {"date": "2025-09-03", "value": 40, "unit": "mg/dL", "reference_range": ">40", "status": "low"},
            ],
        },
        {
            "metric": "total_cholesterol",
            "display_name_he": "כולסטרול כללי",
            "values": [
                {"date": "2022-09-01", "value": 163, "unit": "mg/dL", "reference_range": "<200", "status": "normal"},
                {"date": "2025-09-03", "value": 176, "unit": "mg/dL", "reference_range": "<200", "status": "normal"},
            ],
        },
        {
            "metric": "triglycerides",
            "display_name_he": "טריגליצרידים",
            "values": [
                {"date": "2022-09-01", "value": 100, "unit": "mg/dL", "reference_range": "<150", "status": "normal"},
                {"date": "2025-09-03", "value": 99, "unit": "mg/dL", "reference_range": "<150", "status": "normal"},
            ],
        },
        {
            "metric": "glucose",
            "display_name_he": "גלוקוז",
            "values": [
                {"date": "2022-09-01", "value": 93, "unit": "mg/dL", "reference_range": "74-100", "status": "normal"},
                {"date": "2025-09-03", "value": 97, "unit": "mg/dL", "reference_range": "74-100", "status": "normal"},
            ],
        },
        {
            "metric": "HbA1c",
            "display_name_he": "המוגלובין מסוכרר",
            "values": [
                {"date": "2025-09-03", "value": 5.4, "unit": "%", "reference_range": "<5.7", "status": "normal"},
            ],
        },
        {
            "metric": "vitamin_d",
            "display_name_he": "ויטמין D",
            "values": [
                {"date": "2025-09-03", "value": 20, "unit": "ng/mL", "reference_range": "30-100", "status": "low"},
            ],
        },
        {
            "metric": "eGFR",
            "display_name_he": "תפקוד כליות (eGFR)",
            "values": [
                {"date": "2025-09-03", "value": 75, "unit": "mL/min", "reference_range": ">90", "status": "low"},
            ],
        },
        {
            "metric": "creatinine",
            "display_name_he": "קריאטינין",
            "values": [
                {"date": "2022-09-01", "value": 1.08, "unit": "mg/dL", "reference_range": "0.67-1.17", "status": "normal"},
                {"date": "2025-09-03", "value": 1.23, "unit": "mg/dL", "reference_range": "0.67-1.17", "status": "high"},
            ],
        },
        {
            "metric": "hemoglobin",
            "display_name_he": "המוגלובין",
            "values": [
                {"date": "2022-09-01", "value": 15.5, "unit": "g/dL", "reference_range": "14-18", "status": "normal"},
                {"date": "2025-09-03", "value": 15.9, "unit": "g/dL", "reference_range": "14-18", "status": "normal"},
            ],
        },
        {
            "metric": "TSH",
            "display_name_he": "תירואיד (TSH)",
            "values": [
                {"date": "2025-09-03", "value": 2.59, "unit": "IU/L", "reference_range": "0.55-4.78", "status": "normal"},
            ],
        },
        {
            "metric": "vitamin_b12",
            "display_name_he": "ויטמין B12",
            "values": [
                {"date": "2025-09-03", "value": 387, "unit": "pg/mL", "reference_range": "211-911", "status": "normal"},
            ],
        },
    ]

    r = httpx.post(f"{API_URL}/v1/medical/lab-trends", headers=HEADERS,
                   content=json.dumps({"trends": trends}, ensure_ascii=False))
    print(f"Lab trends: {r.status_code}")


if __name__ == "__main__":
    seed_goal_program()
    seed_lab_trends()
    print("Done!")
