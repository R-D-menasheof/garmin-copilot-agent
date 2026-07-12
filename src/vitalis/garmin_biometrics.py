"""Map raw Garmin Connect responses into app-facing daily biometrics.

This module is the SSOT for the direct-Garmin-to-cloud projection. Raw Garmin
JSON remains available locally for deep analysis; the projection gives the
multi-user context packet stable daily fields, including Garmin-only recovery
metrics that Health Connect does not reliably expose.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from vitalis.models import BiometricsRecord


def _number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _positive_int(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None and number > 0 else None


def _float(value: Any) -> float | None:
    number = _number(value)
    return float(number) if number is not None else None


def _items(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
            elif isinstance(item, list):
                yield from _items(item)


def _day(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _record_payload(records: dict[date, dict[str, Any]], day: date) -> dict[str, Any]:
    payload = records.setdefault(day, {"date": day, "source": "garmin_direct"})
    return payload


def _set(payload: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        payload[key] = value


def _sleep_score(dto: dict[str, Any]) -> int | None:
    scores = dto.get("sleepScores")
    if isinstance(scores, dict):
        overall = scores.get("overall")
        if isinstance(overall, dict):
            score = _positive_int(overall.get("value"))
            if score is not None:
                return score
    return _positive_int(dto.get("sleepScoreOverall") or dto.get("overallSleepScore"))


def _heart_rate_average(item: dict[str, Any]) -> int | None:
    values = item.get("heartRateValues")
    if not isinstance(values, list):
        return None
    samples: list[float] = []
    for pair in values:
        if isinstance(pair, list) and len(pair) >= 2:
            value = _number(pair[1])
            if value is not None and value > 0:
                samples.append(float(value))
    return round(sum(samples) / len(samples)) if samples else None


def extract_garmin_biometrics(raw_data: dict[str, Any]) -> dict[date, BiometricsRecord]:
    """Project a ``GarminClient.fetch_all`` result into daily records."""
    records: dict[date, dict[str, Any]] = {}

    for item in _items(raw_data.get("daily_stats", [])):
        day = _day(item.get("calendarDate"))
        if day is None:
            continue
        payload = _record_payload(records, day)
        _set(payload, "steps", _positive_int(item.get("totalSteps")))
        _set(payload, "resting_hr", _positive_int(item.get("restingHeartRate")))
        _set(payload, "max_hr", _positive_int(item.get("maxHeartRate")))
        _set(payload, "active_calories", _positive_int(item.get("activeKilocalories")))
        _set(payload, "total_calories", _positive_int(item.get("totalKilocalories")))
        _set(payload, "floors_climbed", _positive_int(item.get("floorsAscended")))
        _set(payload, "distance_meters", _float(item.get("totalDistanceMeters")))
        _set(payload, "sleep_seconds", _positive_int(item.get("sleepingSeconds")))
        _set(payload, "spo2_pct", _float(item.get("averageSpo2")))
        _set(payload, "respiratory_rate", _float(item.get("avgWakingRespirationValue")))
        _set(payload, "body_battery_high", _positive_int(item.get("bodyBatteryHighestValue")))
        _set(payload, "body_battery_low", _positive_int(item.get("bodyBatteryLowestValue")))
        _set(payload, "body_battery_at_wake", _positive_int(item.get("bodyBatteryAtWakeTime")))
        _set(payload, "stress_avg", _positive_int(item.get("averageStressLevel")))
        _set(payload, "stress_max", _positive_int(item.get("maxStressLevel")))
        moderate = _positive_int(item.get("moderateIntensityMinutes"))
        vigorous = _positive_int(item.get("vigorousIntensityMinutes"))
        _set(payload, "moderate_intensity_minutes", moderate)
        _set(payload, "vigorous_intensity_minutes", vigorous)
        if moderate is not None or vigorous is not None:
            payload["intensity_minutes"] = (moderate or 0) + 2 * (vigorous or 0)

    for item in _items(raw_data.get("heart_rate", [])):
        day = _day(item.get("calendarDate"))
        if day is None:
            continue
        payload = _record_payload(records, day)
        _set(payload, "resting_hr", _positive_int(item.get("restingHeartRate")))
        _set(payload, "avg_hr", _heart_rate_average(item))
        _set(payload, "max_hr", _positive_int(item.get("maxHeartRate")))

    for item in _items(raw_data.get("sleep", [])):
        dto = item.get("dailySleepDTO") if isinstance(item.get("dailySleepDTO"), dict) else item
        day = _day(dto.get("calendarDate"))
        if day is None:
            continue
        payload = _record_payload(records, day)
        _set(payload, "sleep_seconds", _positive_int(dto.get("sleepTimeSeconds")))
        _set(payload, "deep_sleep_seconds", _positive_int(dto.get("deepSleepSeconds")))
        _set(payload, "light_sleep_seconds", _positive_int(dto.get("lightSleepSeconds")))
        _set(payload, "rem_sleep_seconds", _positive_int(dto.get("remSleepSeconds")))
        _set(payload, "awake_sleep_seconds", _positive_int(dto.get("awakeSleepSeconds")))
        _set(payload, "sleep_score", _sleep_score(dto))
        _set(payload, "spo2_pct", _float(dto.get("averageSpO2Value")))
        _set(payload, "respiratory_rate", _float(dto.get("averageRespirationValue")))
        _set(payload, "avg_hr", _positive_int(dto.get("avgHeartRate")))

    for item in _items(raw_data.get("hrv", [])):
        summary = item.get("hrvSummary")
        if not isinstance(summary, dict):
            continue
        day = _day(summary.get("calendarDate"))
        if day is not None:
            _set(_record_payload(records, day), "hrv_ms", _positive_int(summary.get("lastNightAvg")))

    for item in _items(raw_data.get("spo2", [])):
        day = _day(item.get("calendarDate"))
        if day is not None:
            value = item.get("averageSpO2") or item.get("avgSleepSpO2")
            _set(_record_payload(records, day), "spo2_pct", _float(value))

    for item in _items(raw_data.get("respiration", [])):
        day = _day(item.get("calendarDate"))
        if day is not None:
            value = item.get("avgSleepRespirationValue") or item.get("avgWakingRespirationValue")
            _set(_record_payload(records, day), "respiratory_rate", _float(value))

    for item in _items(raw_data.get("intensity_minutes", [])):
        day = _day(item.get("calendarDate"))
        if day is None:
            continue
        payload = _record_payload(records, day)
        moderate = _positive_int(item.get("moderateMinutes"))
        vigorous = _positive_int(item.get("vigorousMinutes"))
        _set(payload, "moderate_intensity_minutes", moderate)
        _set(payload, "vigorous_intensity_minutes", vigorous)
        if moderate is not None or vigorous is not None:
            payload["intensity_minutes"] = (moderate or 0) + 2 * (vigorous or 0)

    for item in _items(raw_data.get("hydration", [])):
        day = _day(item.get("calendarDate"))
        if day is not None:
            _set(_record_payload(records, day), "water_ml", _float(item.get("valueInML")))

    for item in _items(raw_data.get("training_readiness", [])):
        day = _day(item.get("calendarDate"))
        if day is not None:
            _set(_record_payload(records, day), "training_readiness", _positive_int(item.get("score")))

    activities_by_day: dict[date, list[dict[str, Any]]] = {}
    for item in _items(raw_data.get("activities", [])):
        day = _day(item.get("startTimeLocal") or item.get("startTimeGMT"))
        if day is not None:
            activities_by_day.setdefault(day, []).append(item)
    for day, activities in activities_by_day.items():
        payload = _record_payload(records, day)
        valid_activities = [
            activity
            for activity in activities
            if (_float(activity.get("duration")) or 0.0) >= 60.0
        ]
        payload["activity_count"] = len(valid_activities)
        activity_types: list[str] = []
        duration_seconds = 0.0
        weighted_hr_total = 0.0
        weighted_hr_seconds = 0.0
        activity_max_hr: int | None = None
        for activity in valid_activities:
            activity_type = activity.get("activityType")
            if isinstance(activity_type, dict):
                type_name = activity_type.get("typeKey")
            else:
                type_name = activity_type
            if isinstance(type_name, str) and type_name not in activity_types:
                activity_types.append(type_name)
            duration = _float(activity.get("duration")) or 0.0
            duration_seconds += duration
            average_hr = _float(activity.get("averageHR"))
            if average_hr is not None and duration > 0:
                weighted_hr_total += average_hr * duration
                weighted_hr_seconds += duration
            max_hr = _positive_int(activity.get("maxHR"))
            if max_hr is not None:
                activity_max_hr = max(max_hr, activity_max_hr or max_hr)
        payload["activity_types"] = activity_types
        payload["exercise_minutes"] = round(duration_seconds / 60)
        if weighted_hr_seconds > 0 and payload.get("avg_hr") is None:
            payload["avg_hr"] = round(weighted_hr_total / weighted_hr_seconds)
        if activity_max_hr is not None:
            payload["max_hr"] = max(activity_max_hr, payload.get("max_hr") or activity_max_hr)

    for container_name in ("body_composition", "weigh_ins"):
        containers = raw_data.get(container_name, [])
        for container in _items(containers):
            rows: list[dict[str, Any]] = []
            nested = container.get("dateWeightList")
            if isinstance(nested, list):
                rows.extend(row for row in nested if isinstance(row, dict))
            summaries = container.get("dailyWeightSummaries")
            if isinstance(summaries, list):
                rows.extend(
                    summary["latestWeight"]
                    for summary in summaries
                    if isinstance(summary, dict) and isinstance(summary.get("latestWeight"), dict)
                )
            for row in rows:
                day = _day(row.get("calendarDate"))
                if day is None:
                    continue
                payload = _record_payload(records, day)
                weight = _float(row.get("weight"))
                if weight is not None and weight > 500:
                    weight /= 1000
                _set(payload, "weight_kg", weight)
                _set(payload, "body_fat_pct", _float(row.get("bodyFat")))
                _set(payload, "bmi", _float(row.get("bmi")))

    return {
        day: BiometricsRecord.model_validate(payload)
        for day, payload in sorted(records.items())
    }


def merge_biometrics_records(
    existing: BiometricsRecord | None,
    incoming: BiometricsRecord,
) -> BiometricsRecord:
    """Merge sources, preferring non-null incoming Garmin values."""
    if existing is None:
        return incoming
    if existing.date != incoming.date:
        raise ValueError("Cannot merge biometrics from different dates")

    merged = existing.model_dump(mode="python")
    merged.update(incoming.model_dump(mode="python", exclude_none=True))

    sources: list[str] = []
    for source in (incoming.source, existing.source):
        for part in source.split("+") if source else []:
            if part and part not in sources:
                sources.append(part)
    merged["source"] = "+".join(sources)
    return BiometricsRecord.model_validate(merged)