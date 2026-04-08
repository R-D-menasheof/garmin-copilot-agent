"""Write API — mutation endpoints for meals, goals, and biometrics."""

from __future__ import annotations

import json
import logging
from datetime import date

from pydantic import ValidationError

from shared.auth import verify_api_key
from shared.blob_store import BlobStore
from vitalis.models import (
    AnalysisSummary,
    BiometricsRecord,
    FavoriteMeal,
    GoalProgram,
    KnownFood,
    LabTrend,
    MealEntry,
    MealTemplate,
    NutritionGoal,
    PlanDay,
    RecStatus,
    RecommendationStatus,
    SleepChecklist,
    SleepEntry,
    TimelineEvent,
    TrainingProgram,
)

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


def _ok(data: dict, status_code: int = 201) -> "HttpResponse":
    from azure.functions import HttpResponse
    return HttpResponse(
        json.dumps(data, ensure_ascii=False, default=str),
        status_code=status_code,
        mimetype="application/json",
    )


def post_meal(req) -> "HttpResponse":
    """POST /api/v1/meals — log a meal entry."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        meal = MealEntry.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid meal data: {e}")

    store = _get_blob_store()
    day = meal.timestamp.date()

    # Append to existing meals for the day
    existing = store.load_meals(day)
    existing.append(meal)
    store.save_meals(day, existing)

    # Cache this food for future fuzzy matching
    food = KnownFood(
        food_name=meal.food_name,
        calories_per_100g=meal.calories,
        protein_per_100g=meal.protein_g,
        carbs_per_100g=meal.carbs_g,
        fat_per_100g=meal.fat_g,
        source=meal.source,
    )
    store.append_food_cache(food)

    logger.info("Stored meal: %s (%d kcal)", meal.food_name, meal.calories)
    return _ok({"status": "ok", "meal": meal.model_dump(mode="json")})


def put_meals(req) -> "HttpResponse":
    """PUT /api/v1/meals — replace all meals for a single day."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
        day = date.fromisoformat(body["date"])
        meals = [MealEntry.model_validate(item) for item in body["meals"]]
    except (KeyError, TypeError, ValueError, ValidationError) as e:
        return _error(f"Invalid meals data: {e}")

    store = _get_blob_store()
    store.save_meals(day, meals)

    logger.info("Replaced %d meals for %s", len(meals), day)
    return _ok(
        {
            "status": "ok",
            "date": day.isoformat(),
            "meals": [meal.model_dump(mode="json") for meal in meals],
        },
        status_code=200,
    )


def post_goals(req) -> "HttpResponse":
    """POST /api/v1/goals — set nutrition goals."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        goal = NutritionGoal.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid goal data: {e}")

    store = _get_blob_store()
    store.save_goals(goal)

    logger.info("Stored goals: %d kcal target", goal.calories_target)
    return _ok({"status": "ok", "goal": goal.model_dump(mode="json")})


def post_biometrics(req) -> "HttpResponse":
    """POST /api/v1/biometrics — store biometrics from Health Connect."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        record = BiometricsRecord.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid biometrics data: {e}")

    store = _get_blob_store()
    store.save_biometrics(record.date, record)

    logger.info("Stored biometrics for %s", record.date)
    return _ok({"status": "ok", "biometrics": record.model_dump(mode="json")})


def post_favorite(req) -> "HttpResponse":
    """POST /api/v1/favorites — save a favorite meal."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        favorite = FavoriteMeal.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid favorite data: {e}")

    store = _get_blob_store()
    store.save_favorite(favorite)
    return _ok({"status": "ok", "favorite": favorite.model_dump(mode="json")})


def delete_favorite(req) -> "HttpResponse":
    """DELETE /api/v1/favorites?id=ID — delete a favorite meal."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    favorite_id = req.params.get("id")
    if not favorite_id:
        return _error("'id' query param required")

    store = _get_blob_store()
    store.delete_favorite(favorite_id)
    return _ok({"status": "ok", "id": favorite_id}, status_code=200)


def post_template(req) -> "HttpResponse":
    """POST /api/v1/templates — save a meal template."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        template = MealTemplate.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid template data: {e}")

    store = _get_blob_store()
    store.save_template(template)
    return _ok({"status": "ok", "template": template.model_dump(mode="json")})


def delete_template(req) -> "HttpResponse":
    """DELETE /api/v1/templates?id=ID — delete a meal template."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    template_id = req.params.get("id")
    if not template_id:
        return _error("'id' query param required")

    store = _get_blob_store()
    store.delete_template(template_id)
    return _ok({"status": "ok", "id": template_id}, status_code=200)


def post_plan_day(req) -> "HttpResponse":
    """POST /api/v1/plan — save a day's meal plan."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        plan_day = PlanDay.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid plan data: {e}")

    store = _get_blob_store()
    store.save_plan_day(plan_day)
    return _ok({"status": "ok", "plan": plan_day.model_dump(mode="json")})


def post_summary(req) -> "HttpResponse":
    """POST /api/v1/summary — publish a weekly analysis summary."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        summary = AnalysisSummary.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid summary data: {e}")

    store = _get_blob_store()
    store.save_summary(summary)
    return _ok({"status": "ok", "summary": summary.model_dump(mode="json")})


def post_recommendation_status(req) -> "HttpResponse":
    """POST /api/v1/recommendations/status — update a recommendation's adoption status."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
        rec_id = body["rec_id"]
        status_str = body["status"]
        status = RecStatus(status_str)
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return _error(f"Invalid request: {e}")

    store = _get_blob_store()
    statuses = store.load_recommendation_statuses()

    from datetime import datetime as dt

    updated = False
    for s in statuses:
        if s.rec_id == rec_id:
            s.status = status
            s.updated_at = dt.now()
            updated = True
            break

    if not updated:
        statuses.append(
            RecommendationStatus(rec_id=rec_id, status=status, updated_at=dt.now())
        )

    store.save_recommendation_statuses(statuses)
    return _ok({"status": "ok", "rec_id": rec_id, "new_status": status_str})


def post_timeline_event(req) -> "HttpResponse":
    """POST /api/v1/timeline — add a timeline event."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        event = TimelineEvent.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid timeline event: {e}")

    store = _get_blob_store()
    store.append_timeline_event(event)
    return _ok({"status": "ok", "event": event.model_dump(mode="json")})


def post_training_program(req) -> "HttpResponse":
    """POST /api/v1/training — save a training program."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        program = TrainingProgram.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid training program: {e}")

    store = _get_blob_store()
    store.save_training_program(program)
    return _ok({"status": "ok", "program": program.model_dump(mode="json")})


def patch_training_session(req) -> "HttpResponse":
    """PATCH /api/v1/training/session — mark a session completed."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
        week = body["week"]
        session_idx = body["session"]
        completed = body.get("completed", True)
    except (json.JSONDecodeError, KeyError) as e:
        return _error(f"Invalid request: {e}")

    store = _get_blob_store()
    program = store.load_active_training_program()
    if program is None:
        return _error("No active training program", 404)

    if week < 0 or week >= len(program.weeks):
        return _error("Invalid week index")
    if session_idx < 0 or session_idx >= len(program.weeks[week].sessions):
        return _error("Invalid session index")

    program.weeks[week].sessions[session_idx].completed = completed
    store.save_training_program(program)
    return _ok({"status": "ok"}, status_code=200)


def post_goal_program(req) -> "HttpResponse":
    """POST /api/v1/goals/programs — save a goal program."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        program = GoalProgram.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid goal program: {e}")

    store = _get_blob_store()
    store.save_goal_program(program)
    return _ok({"status": "ok", "program": program.model_dump(mode="json")})


def post_sleep_protocol(req) -> "HttpResponse":
    """POST /api/v1/sleep/protocol — save sleep checklist."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        checklist = SleepChecklist.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid sleep protocol: {e}")

    store = _get_blob_store()
    store.save_sleep_protocol(checklist)
    return _ok({"status": "ok", "protocol": checklist.model_dump(mode="json")})


def post_sleep_entry(req) -> "HttpResponse":
    """POST /api/v1/sleep/entry — log a sleep entry."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        entry = SleepEntry.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid sleep entry: {e}")

    store = _get_blob_store()
    store.save_sleep_entry(entry)
    return _ok({"status": "ok", "entry": entry.model_dump(mode="json")})


def post_lab_trends(req) -> "HttpResponse":
    """POST /api/v1/medical/lab-trends — save parsed lab trends."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
        trends = [LabTrend.model_validate(item) for item in body.get("trends", [])]
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        return _error(f"Invalid lab trends: {e}")

    store = _get_blob_store()
    store.save_lab_trends(trends)
    return _ok({"status": "ok", "count": len(trends)})
