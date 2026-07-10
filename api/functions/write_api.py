"""Write API — mutation endpoints for meals, goals, and biometrics."""

from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import date

from pydantic import ValidationError

from shared.auth import resolve_identity, resolve_user, verify_api_key
from shared.blob_store import BlobStore
from vitalis.models import (
    AnalysisSummary,
    BiometricsRecord,
    DayTrackingOverride,
    FavoriteMeal,
    GoalProgram,
    KnownFood,
    LabTrend,
    MealEntry,
    MealTemplate,
    MedicalUpload,
    NutritionGoal,
    PlanDay,
    Profile,
    PushToken,
    RecStatus,
    RecommendationStatus,
    SleepChecklist,
    SleepEntry,
    TimelineEvent,
    TrainingProgram,
)

logger = logging.getLogger(__name__)

# Wearable-sourced fields the client may never overwrite via PATCH /v1/profile.
_AUTO_SYNCED_FIELDS = frozenset({
    "weight_kg", "body_fat_pct", "bmi", "vo2max", "fitness_age",
    "resting_heart_rate", "devices", "last_synced",
})

# Medical upload guards (in-app document upload; extraction is owner-side).
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_UPLOAD_TYPES = frozenset({
    "application/pdf", "image/jpeg", "image/png",
})


def _get_blob_store(req) -> BlobStore:
    """Create a user-scoped BlobStore for the authenticated caller.

    The ``user_id`` is resolved server-side from the request credentials and
    never taken from client-supplied input, so a caller can only ever write
    to their own ``users/{user_id}/`` data. Mockable in tests.
    """
    user_id = resolve_user(req)
    if not user_id:
        raise PermissionError("Unauthenticated request reached blob store")
    return BlobStore(user_id=user_id)


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


def _notify_report_ready(store, date_iso: str) -> int:
    """Best-effort 'report ready' push. Never fails the request."""
    try:
        from shared.notifications import notify_report_ready

        return notify_report_ready(store, date_iso)
    except Exception as exc:  # notifications must never block publishing
        logger.warning("Report-ready notification failed: %s", exc)
        return 0


def post_meal(req) -> "HttpResponse":
    """POST /api/v1/meals — log a meal entry."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        meal = MealEntry.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid meal data: {e}")

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
    store.save_favorite(favorite)
    return _ok({"status": "ok", "favorite": favorite.model_dump(mode="json")})


def delete_favorite(req) -> "HttpResponse":
    """DELETE /api/v1/favorites?id=ID — delete a favorite meal."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    favorite_id = req.params.get("id")
    if not favorite_id:
        return _error("'id' query param required")

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
    store.save_template(template)
    return _ok({"status": "ok", "template": template.model_dump(mode="json")})


def delete_template(req) -> "HttpResponse":
    """DELETE /api/v1/templates?id=ID — delete a meal template."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    template_id = req.params.get("id")
    if not template_id:
        return _error("'id' query param required")

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
    store.save_summary(summary)
    notified = _notify_report_ready(store, summary.date.isoformat())
    return _ok(
        {
            "status": "ok",
            "notified": notified,
            "summary": summary.model_dump(mode="json"),
        }
    )


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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
    store.append_timeline_event(event)
    return _ok({"status": "ok", "event": event.model_dump(mode="json")})


def put_timeline(req) -> "HttpResponse":
    """PUT /api/v1/timeline — replace all timeline events."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
        events = [TimelineEvent.model_validate(item) for item in body["events"]]
    except (KeyError, TypeError, ValueError, ValidationError) as e:
        return _error(f"Invalid timeline data: {e}")

    store = _get_blob_store(req)
    store.save_timeline_events(events)

    logger.info("Replaced timeline with %d events", len(events))
    return _ok(
        {
            "status": "ok",
            "events": [e.model_dump(mode="json") for e in events],
        },
        status_code=200,
    )


def post_training_program(req) -> "HttpResponse":
    """POST /api/v1/training — save a training program."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        program = TrainingProgram.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid training program: {e}")

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
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

    store = _get_blob_store(req)
    store.save_lab_trends(trends)
    return _ok({"status": "ok", "count": len(trends)})


def post_day_override(req) -> "HttpResponse":
    """POST /api/v1/nutrition/day-override — toggle whether a day counts in balance calcs."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
        override_date = date.fromisoformat(body["date"])
        tracked = bool(body["tracked"])
        note = body.get("note", "")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return _error(f"Invalid request: {e}")

    store = _get_blob_store(req)
    overrides = store.load_day_overrides()
    from datetime import datetime as dt

    updated = False
    for o in overrides:
        if o.date == override_date:
            o.tracked = tracked
            o.note = note
            o.updated_at = dt.now()
            updated = True
            break
    if not updated:
        overrides.append(DayTrackingOverride(date=override_date, tracked=tracked, note=note))

    store.save_day_overrides(overrides)
    return _ok({"status": "ok", "date": override_date.isoformat(), "tracked": tracked})


def patch_profile(req) -> "HttpResponse":
    """PATCH /api/v1/profile — merge user-editable fields into the profile.

    Only the fields present in the request body are updated; all other fields
    (including auto-synced wearable metrics, which the client may never
    overwrite) are preserved.
    """
    identity = resolve_identity(req)
    if identity is None:
        return _error("Unauthorized", 401)

    try:
        changes = json.loads(req.get_body())
        if not isinstance(changes, dict):
            raise ValueError("body must be a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        return _error(f"Invalid profile data: {e}")

    store = _get_blob_store(req)
    existing = store.load_profile()
    if existing is None:
        existing = Profile(display_name=identity.name, email=identity.email)

    merged = existing.model_dump(mode="json")
    for key, value in changes.items():
        if key in _AUTO_SYNCED_FIELDS:
            continue  # never let the client overwrite wearable-sourced data
        merged[key] = value

    try:
        updated = Profile.model_validate(merged)
    except ValidationError as e:
        return _error(f"Invalid profile data: {e}")

    store.save_profile(updated)
    return _ok({"profile": updated.model_dump(mode="json")}, status_code=200)


def post_push_token(req) -> "HttpResponse":
    """POST /api/v1/push/register — register/refresh this device's push token."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        token = PushToken.model_validate_json(req.get_body())
    except (ValidationError, ValueError) as e:
        return _error(f"Invalid push token: {e}")

    store = _get_blob_store(req)
    store.save_push_token(token)
    logger.info("Registered push token for platform %s", token.platform)
    return _ok({"status": "ok", "token": token.model_dump(mode="json")})


def unregister_push_token(req) -> "HttpResponse":
    """DELETE /api/v1/push/token?token=... — unregister a device's push token."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    token_str = req.params.get("token")
    if not token_str:
        return _error("'token' query param required")

    store = _get_blob_store(req)
    store.delete_push_token(token_str)
    return _ok({"status": "ok"}, status_code=200)


def post_medical_upload(req) -> "HttpResponse":
    """POST /api/v1/medical/upload — upload a medical document (base64 body).

    Stores the raw file under the user's scope for later owner-side extraction
    (Phase 6.3). No extraction happens here; ``extracted`` stays False.
    """
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    try:
        body = json.loads(req.get_body())
    except (json.JSONDecodeError, ValueError):
        return _error("Invalid JSON body")

    filename = body.get("filename")
    content_b64 = body.get("content")
    content_type = body.get("content_type", "")
    if not filename or not content_b64:
        return _error("'filename' and 'content' (base64) required")
    if content_type not in _ALLOWED_UPLOAD_TYPES:
        return _error(
            "Unsupported content_type. Allowed: "
            + ", ".join(sorted(_ALLOWED_UPLOAD_TYPES))
        )

    try:
        content = base64.b64decode(content_b64)
    except Exception:
        return _error("Invalid base64 content")

    if not content:
        return _error("Empty file")
    if len(content) > _MAX_UPLOAD_BYTES:
        return _error("File too large (max 10 MB)", 413)

    upload = MedicalUpload(
        id=uuid.uuid4().hex,
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        category=body.get("category", ""),
        note=body.get("note", ""),
    )
    store = _get_blob_store(req)
    store.save_medical_upload(upload, content)
    logger.info("Stored medical upload %s", upload.filename)
    return _ok({"status": "ok", "upload": upload.model_dump(mode="json")})
