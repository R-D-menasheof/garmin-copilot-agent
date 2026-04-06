"""Regression tests for image-retention behavior in ingestion endpoints."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from functions.ingestion import analyze_image
from vitalis.models import MealEntry, NutritionSource


def _make_request(body: dict, headers: dict | None = None) -> MagicMock:
    req = MagicMock()
    req.get_body.return_value = json.dumps(body).encode()
    req.headers = headers or {"x-api-key": "test-key"}
    return req


def _meal(name: str = "banana") -> MealEntry:
    return MealEntry(
        food_name=name,
        calories=89,
        protein_g=1.1,
        carbs_g=22.8,
        fat_g=0.3,
        source=NutritionSource.LLM,
        timestamp=datetime(2026, 4, 4, 12, 0),
    )


@patch("functions.ingestion._get_blob_store")
@patch("functions.ingestion.verify_api_key", return_value=True)
@patch("functions.ingestion.analyze_food_image", return_value=[_meal("חזה עוף")])
def test_analyze_image_does_not_persist_raw_uploads(
    _vision: MagicMock,
    _auth: MagicMock,
    mock_store_fn: MagicMock,
) -> None:
    store = MagicMock()
    mock_store_fn.return_value = store

    img = base64.b64encode(b"fake-image").decode()
    req = _make_request({"image": img})

    resp = analyze_image(req)

    assert resp.status_code == 200
    assert len(store.method_calls) == 1
    assert store.method_calls[0][0] == "append_food_cache"
    store.save_meals.assert_not_called()
    store.save_goals.assert_not_called()
    store.save_biometrics.assert_not_called()