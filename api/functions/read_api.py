"""Read API — GET endpoints for nutrition, biometrics, combined data."""

from __future__ import annotations

import json
import logging
from datetime import date

from shared.auth import verify_api_key
from shared.blob_store import BlobStore

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


def _parse_date(value: str) -> date | None:
    """Parse YYYY-MM-DD string to date, or None on failure."""
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_limit(value: str | None, default: int = 10) -> int | None:
    """Parse an integer query param limit, or None on failure."""
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def get_nutrition(req) -> "HttpResponse":
    """GET /api/v1/nutrition?from=DATE&to=DATE — return meals for range."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    from_str = req.params.get("from")
    to_str = req.params.get("to")
    if not from_str or not to_str:
        return _error("'from' and 'to' query params required")

    start = _parse_date(from_str)
    end = _parse_date(to_str)
    if start is None or end is None:
        return _error("Invalid date format. Use YYYY-MM-DD")

    store = _get_blob_store()
    meals = store.load_meals_range(start, end)

    return _ok({
        "meals": {
            d.isoformat(): [m.model_dump(mode="json") for m in ms]
            for d, ms in meals.items()
        }
    })


def get_biometrics(req) -> "HttpResponse":
    """GET /api/v1/biometrics?from=DATE&to=DATE — return biometrics for range."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    from_str = req.params.get("from")
    to_str = req.params.get("to")
    if not from_str or not to_str:
        return _error("'from' and 'to' query params required")

    start = _parse_date(from_str)
    end = _parse_date(to_str)
    if start is None or end is None:
        return _error("Invalid date format. Use YYYY-MM-DD")

    store = _get_blob_store()
    biometrics = store.load_biometrics_range(start, end)

    return _ok({
        "biometrics": {
            d.isoformat(): b.model_dump(mode="json")
            for d, b in biometrics.items()
        }
    })


def get_combined(req) -> "HttpResponse":
    """GET /api/v1/combined?from=DATE&to=DATE — merged nutrition + biometrics."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    from_str = req.params.get("from")
    to_str = req.params.get("to")
    if not from_str or not to_str:
        return _error("'from' and 'to' query params required")

    start = _parse_date(from_str)
    end = _parse_date(to_str)
    if start is None or end is None:
        return _error("Invalid date format. Use YYYY-MM-DD")

    store = _get_blob_store()
    combined = store.load_combined(start, end)

    return _ok(combined)


def get_goals(req) -> "HttpResponse":
    """GET /api/v1/goals — return current nutrition goals."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    goal = store.load_goals()

    if goal is None:
        return _ok({"goal": None})

    return _ok({"goal": goal.model_dump(mode="json")})


def get_recents(req) -> "HttpResponse":
    """GET /api/v1/recents?limit=N — return recent unique meals."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    limit = _parse_limit(req.params.get("limit"))
    if limit is None:
        return _error("Invalid 'limit' query param")

    store = _get_blob_store()
    recents = store.load_recent_meals(limit=limit)
    return _ok({"recents": [meal.model_dump(mode="json") for meal in recents]})


def get_favorites(req) -> "HttpResponse":
    """GET /api/v1/favorites — return saved favorite meals."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    favorites = store.load_favorites()
    return _ok({"favorites": [favorite.model_dump(mode="json") for favorite in favorites]})


def get_templates(req) -> "HttpResponse":
    """GET /api/v1/templates — return saved meal templates."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    templates = store.load_templates()
    return _ok({"templates": [template.model_dump(mode="json") for template in templates]})


def get_plan_day(req) -> "HttpResponse":
    """GET /api/v1/plan?date=DATE — return a day's meal plan."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    day_str = req.params.get("date")
    if not day_str:
        return _error("'date' query param required")

    day = _parse_date(day_str)
    if day is None:
        return _error("Invalid date format. Use YYYY-MM-DD")

    store = _get_blob_store()
    plan = store.load_plan_day(day)
    return _ok({"plan": None if plan is None else plan.model_dump(mode="json")})


def get_latest_summary(req) -> "HttpResponse":
    """GET /api/v1/summary/latest — return the latest published summary."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    summary = store.load_latest_summary()
    return _ok({"summary": None if summary is None else summary.model_dump(mode="json")})


def get_summary_history(req) -> "HttpResponse":
    """GET /api/v1/summary/history?limit=N — return published summary history."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    limit = _parse_limit(req.params.get("limit"), default=4)
    if limit is None:
        return _error("Invalid 'limit' query param")

    store = _get_blob_store()
    summaries = store.load_summary_history(limit=limit)
    return _ok({"summaries": [summary.model_dump(mode="json") for summary in summaries]})


def get_recommendation_statuses(req) -> "HttpResponse":
    """GET /api/v1/recommendations/status — return recommendation adoption statuses."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    statuses = store.load_recommendation_statuses()
    return _ok({"statuses": [s.model_dump(mode="json") for s in statuses]})


def get_timeline(req) -> "HttpResponse":
    """GET /api/v1/timeline — return health timeline events."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    events = store.load_timeline_events()
    return _ok({"events": [e.model_dump(mode="json") for e in events]})


def get_active_training(req) -> "HttpResponse":
    """GET /api/v1/training/active — return active training program."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    program = store.load_active_training_program()
    return _ok({"program": None if program is None else program.model_dump(mode="json")})


def get_goal_programs(req) -> "HttpResponse":
    """GET /api/v1/goals/programs — return all goal programs."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    programs = store.load_goal_programs()
    return _ok({"programs": [p.model_dump(mode="json") for p in programs]})


def get_sleep_protocol(req) -> "HttpResponse":
    """GET /api/v1/sleep/protocol — return sleep checklist."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    protocol = store.load_sleep_protocol()
    return _ok({"protocol": None if protocol is None else protocol.model_dump(mode="json")})


def get_sleep_entries(req) -> "HttpResponse":
    """GET /api/v1/sleep/entries?from=&to= — return sleep log entries."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    from_str = req.params.get("from")
    to_str = req.params.get("to")
    if not from_str or not to_str:
        return _error("'from' and 'to' query params required")

    start = _parse_date(from_str)
    end = _parse_date(to_str)
    if start is None or end is None:
        return _error("Invalid date format, use YYYY-MM-DD")

    store = _get_blob_store()
    entries = store.load_sleep_entries(start, end)
    return _ok({"entries": [e.model_dump(mode="json") for e in entries]})


def get_lab_trends(req) -> "HttpResponse":
    """GET /api/v1/medical/lab-trends — return parsed lab trends."""
    if not verify_api_key(req):
        return _error("Unauthorized", 401)

    store = _get_blob_store()
    trends = store.load_lab_trends()
    return _ok({"trends": [t.model_dump(mode="json") for t in trends]})
