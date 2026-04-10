"""Ingestion API — POST endpoints for food image/text analysis."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime

from shared.auth import verify_api_key
from shared.blob_store import BlobStore
from shared.food_lookup import search_open_food_facts_barcode_sync
from shared.food_lookup import resolve_food_sync as resolve_food
from shared.vision import analyze_food_image, parse_food_text
from vitalis.models import KnownFood, MealEntry, NutritionSource

logger = logging.getLogger(__name__)


def _get_blob_store() -> BlobStore:
    """Create BlobStore from environment (mockable in tests)."""
    return BlobStore()


def _error(message: str, status_code: int = 400) -> "HttpResponse":
    from azure.functions import HttpResponse
    return HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json",
    )


def _ok(data: dict, status_code: int = 200) -> "HttpResponse":
    from azure.functions import HttpResponse
    return HttpResponse(
        json.dumps(data, ensure_ascii=False, default=str),
        status_code=status_code,
        mimetype="application/json",
    )


def _run_async(coro):
    """Run async code from sync Azure Functions context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def analyze_image(req) -> "HttpResponse":
    """POST /api/v1/analyze-image — analyze food photo with LLM vision.

    The uploaded image is handled in memory only and is not persisted to Blob
    Storage. Only derived nutrition/cache data may be stored.
    """
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
    except (json.JSONDecodeError, ValueError):
        return _error("Invalid JSON body")

    image_b64 = body.get("image")
    if not image_b64:
        return _error("'image' field (base64) required")

    description = body.get("description", "")

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        return _error("Invalid base64 image data")

    meals = analyze_food_image(image_bytes, description=description or None)
    if asyncio.iscoroutine(meals):
        meals = _run_async(meals)
    del image_bytes

    # Intentionally persist only derived food metadata, never the raw image.
    store = _get_blob_store()
    for meal in meals:
        food = KnownFood(
            food_name=meal.food_name,
            calories_per_100g=meal.calories,
            protein_per_100g=meal.protein_g,
            carbs_per_100g=meal.carbs_g,
            fat_per_100g=meal.fat_g,
            source=NutritionSource.LLM,
        )
        store.append_food_cache(food)

    return _ok({"meals": [m.model_dump(mode="json") for m in meals]})


def analyze_text(req) -> "HttpResponse":
    """POST /api/v1/analyze-text — parse free-text food description."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
    except (json.JSONDecodeError, ValueError):
        return _error("Invalid JSON body")

    text = body.get("text", "").strip()
    if not text:
        return _error("'text' field required and cannot be empty")

    try:
        store = _get_blob_store()
        cache = store.load_food_cache()

        # Run cascade: cache → OFF → USDA → signal LLM
        resolved = resolve_food(text, cache)
        if asyncio.iscoroutine(resolved):
            resolved = _run_async(resolved)
        food, source = resolved

        if food is not None and source != NutritionSource.LLM:
            # Resolved without LLM — build MealEntry from KnownFood
            meal = MealEntry(
                food_name=food.food_name,
                calories=food.calories_per_100g,
                protein_g=food.protein_per_100g,
                carbs_g=food.carbs_per_100g,
                fat_g=food.fat_per_100g,
                source=source,
                timestamp=datetime.now(),
                portion_description="100g (estimated)",
            )
            # Cache if new source
            if source != NutritionSource.HISTORY:
                store.append_food_cache(food)

            return _ok({"meals": [meal.model_dump(mode="json")]})

        # LLM fallback
        try:
            meals = parse_food_text(text)
            if asyncio.iscoroutine(meals):
                meals = _run_async(meals)
        except Exception as llm_err:
            logger.error("LLM fallback failed: %s", llm_err)
            return _error(f"LLM analysis failed: {llm_err}", 502)

        for meal in meals:
            food = KnownFood(
                food_name=meal.food_name,
                calories_per_100g=meal.calories,
                protein_per_100g=meal.protein_g,
                carbs_per_100g=meal.carbs_g,
                fat_per_100g=meal.fat_g,
                source=NutritionSource.LLM,
            )
            store.append_food_cache(food)

        return _ok({"meals": [m.model_dump(mode="json") for m in meals]})

    except Exception as e:
        logger.error("analyze_text failed: %s", e, exc_info=True)
        return _error(f"Server error: {e}", 500)


def lookup_barcode(req) -> "HttpResponse":
    """POST /api/v1/barcode — resolve a barcode to a meal candidate."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
    except (json.JSONDecodeError, ValueError):
        return _error("Invalid JSON body")

    barcode = str(body.get("barcode", "")).strip()
    if not barcode:
        return _error("'barcode' field required")

    food = search_open_food_facts_barcode_sync(barcode)
    if food is None:
        return _error("Barcode not found", 404)

    meal = MealEntry(
        food_name=food.food_name,
        calories=food.calories_per_100g,
        protein_g=food.protein_per_100g,
        carbs_g=food.carbs_per_100g,
        fat_g=food.fat_per_100g,
        fiber_g=food.fiber_per_100g,
        portion_description="100g (estimated)",
        source=food.source,
        timestamp=datetime.now(),
    )
    return _ok({"meals": [meal.model_dump(mode="json")]})
