"""Vitalis API — Azure Functions V4 entry point.

Registers all HTTP triggers for the Read, Write, and Ingestion APIs.
"""

from __future__ import annotations

import azure.functions as func

from functions.read_api import (
    get_biometrics,
    get_combined,
    get_favorites,
    get_goals,
    get_latest_summary,
    get_recommendation_statuses,
    get_summary_history,
    get_nutrition,
    get_plan_day,
    get_recents,
    get_templates,
    get_timeline,
    get_active_training,
    get_goal_programs,
    get_sleep_protocol,
    get_sleep_entries,
    get_lab_trends,
)
from functions.write_api import (
    delete_favorite,
    delete_template,
    post_biometrics,
    post_favorite,
    post_goals,
    post_meal,
    post_plan_day,
    post_recommendation_status,
    post_summary,
    post_template,
    post_timeline_event,
    post_training_program,
    patch_training_session,
    post_goal_program,
    post_sleep_protocol,
    post_sleep_entry,
    post_lab_trends,
    put_meals,
)
from functions.ingestion import analyze_image, analyze_text, lookup_barcode

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ── Read API ──────────────────────────────────────────────────────


@app.route(route="v1/nutrition", methods=["GET"])
def api_get_nutrition(req: func.HttpRequest) -> func.HttpResponse:
    return get_nutrition(req)


@app.route(route="v1/biometrics", methods=["GET"])
def api_get_biometrics(req: func.HttpRequest) -> func.HttpResponse:
    return get_biometrics(req)


@app.route(route="v1/combined", methods=["GET"])
def api_get_combined(req: func.HttpRequest) -> func.HttpResponse:
    return get_combined(req)


@app.route(route="v1/goals", methods=["GET"])
def api_get_goals(req: func.HttpRequest) -> func.HttpResponse:
    return get_goals(req)


@app.route(route="v1/recents", methods=["GET"])
def api_get_recents(req: func.HttpRequest) -> func.HttpResponse:
    return get_recents(req)


@app.route(route="v1/favorites", methods=["GET"])
def api_get_favorites(req: func.HttpRequest) -> func.HttpResponse:
    return get_favorites(req)


@app.route(route="v1/templates", methods=["GET"])
def api_get_templates(req: func.HttpRequest) -> func.HttpResponse:
    return get_templates(req)


@app.route(route="v1/plan", methods=["GET"])
def api_get_plan_day(req: func.HttpRequest) -> func.HttpResponse:
    return get_plan_day(req)


@app.route(route="v1/summary/latest", methods=["GET"])
def api_get_latest_summary(req: func.HttpRequest) -> func.HttpResponse:
    return get_latest_summary(req)


@app.route(route="v1/summary/history", methods=["GET"])
def api_get_summary_history(req: func.HttpRequest) -> func.HttpResponse:
    return get_summary_history(req)


@app.route(route="v1/recommendations/status", methods=["GET"])
def api_get_recommendation_statuses(req: func.HttpRequest) -> func.HttpResponse:
    return get_recommendation_statuses(req)


@app.route(route="v1/timeline", methods=["GET"])
def api_get_timeline(req: func.HttpRequest) -> func.HttpResponse:
    return get_timeline(req)


@app.route(route="v1/training/active", methods=["GET"])
def api_get_active_training(req: func.HttpRequest) -> func.HttpResponse:
    return get_active_training(req)


@app.route(route="v1/goals/programs", methods=["GET"])
def api_get_goal_programs(req: func.HttpRequest) -> func.HttpResponse:
    return get_goal_programs(req)


@app.route(route="v1/sleep/protocol", methods=["GET"])
def api_get_sleep_protocol(req: func.HttpRequest) -> func.HttpResponse:
    return get_sleep_protocol(req)


@app.route(route="v1/sleep/entries", methods=["GET"])
def api_get_sleep_entries(req: func.HttpRequest) -> func.HttpResponse:
    return get_sleep_entries(req)


@app.route(route="v1/medical/lab-trends", methods=["GET"])
def api_get_lab_trends(req: func.HttpRequest) -> func.HttpResponse:
    return get_lab_trends(req)


# ── Write API ─────────────────────────────────────────────────────


@app.route(route="v1/meals", methods=["POST"])
def api_post_meal(req: func.HttpRequest) -> func.HttpResponse:
    return post_meal(req)


@app.route(route="v1/meals", methods=["PUT"])
def api_put_meals(req: func.HttpRequest) -> func.HttpResponse:
    return put_meals(req)


@app.route(route="v1/goals", methods=["POST"])
def api_post_goals(req: func.HttpRequest) -> func.HttpResponse:
    return post_goals(req)


@app.route(route="v1/biometrics", methods=["POST"])
def api_post_biometrics(req: func.HttpRequest) -> func.HttpResponse:
    return post_biometrics(req)


@app.route(route="v1/favorites", methods=["POST"])
def api_post_favorite(req: func.HttpRequest) -> func.HttpResponse:
    return post_favorite(req)


@app.route(route="v1/favorites", methods=["DELETE"])
def api_delete_favorite(req: func.HttpRequest) -> func.HttpResponse:
    return delete_favorite(req)


@app.route(route="v1/templates", methods=["POST"])
def api_post_template(req: func.HttpRequest) -> func.HttpResponse:
    return post_template(req)


@app.route(route="v1/templates", methods=["DELETE"])
def api_delete_template(req: func.HttpRequest) -> func.HttpResponse:
    return delete_template(req)


@app.route(route="v1/plan", methods=["POST"])
def api_post_plan_day(req: func.HttpRequest) -> func.HttpResponse:
    return post_plan_day(req)


@app.route(route="v1/summary", methods=["POST"])
def api_post_summary(req: func.HttpRequest) -> func.HttpResponse:
    return post_summary(req)


@app.route(route="v1/recommendations/status", methods=["POST"])
def api_post_recommendation_status(req: func.HttpRequest) -> func.HttpResponse:
    return post_recommendation_status(req)


@app.route(route="v1/timeline", methods=["POST"])
def api_post_timeline_event(req: func.HttpRequest) -> func.HttpResponse:
    return post_timeline_event(req)


@app.route(route="v1/training", methods=["POST"])
def api_post_training_program(req: func.HttpRequest) -> func.HttpResponse:
    return post_training_program(req)


@app.route(route="v1/training/session", methods=["PATCH"])
def api_patch_training_session(req: func.HttpRequest) -> func.HttpResponse:
    return patch_training_session(req)


@app.route(route="v1/goals/programs", methods=["POST"])
def api_post_goal_program(req: func.HttpRequest) -> func.HttpResponse:
    return post_goal_program(req)


@app.route(route="v1/sleep/protocol", methods=["POST"])
def api_post_sleep_protocol(req: func.HttpRequest) -> func.HttpResponse:
    return post_sleep_protocol(req)


@app.route(route="v1/sleep/entry", methods=["POST"])
def api_post_sleep_entry(req: func.HttpRequest) -> func.HttpResponse:
    return post_sleep_entry(req)


@app.route(route="v1/medical/lab-trends", methods=["POST"])
def api_post_lab_trends(req: func.HttpRequest) -> func.HttpResponse:
    return post_lab_trends(req)


# ── Ingestion API ─────────────────────────────────────────────────


@app.route(route="v1/analyze-image", methods=["POST"])
def api_analyze_image(req: func.HttpRequest) -> func.HttpResponse:
    return analyze_image(req)


@app.route(route="v1/analyze-text", methods=["POST"])
def api_analyze_text(req: func.HttpRequest) -> func.HttpResponse:
    return analyze_text(req)


@app.route(route="v1/barcode", methods=["POST"])
def api_lookup_barcode(req: func.HttpRequest) -> func.HttpResponse:
    return lookup_barcode(req)
