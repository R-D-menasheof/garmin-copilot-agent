# Skill: Garmin Data Sync (DEPRECATED)

> **⚠️ DEPRECATED**: This skill is superseded by `fetch-garmin-data.md`, which covers the updated sync pipeline with 30+ data types, `scripts/sync.py` CLI, and date-stamped storage. Use `fetch-garmin-data.md` for all sync-related guidance.

## Overview

Auto-pull health data from Garmin Connect using the `garminconnect` Python library. All API interaction logic lives in `src/vitalis/garmin_client.py` (SSOT).

## Authentication

- Credentials stored in `.env` as `GARMIN_EMAIL` and `GARMIN_PASSWORD`
- `.env` is in `.gitignore` — never committed
- The library authenticates via Garmin SSO (username/password login)
- Sessions may expire — handle re-authentication gracefully

## Available Data Types

| Data Type        | garminconnect Method           | Our Model            |
| ---------------- | ------------------------------ | -------------------- |
| Activities       | `get_activities(start, limit)` | `ActivityRecord`     |
| Daily Stats      | `get_stats(date)`              | `DailyStats`         |
| Heart Rate       | `get_heart_rates(date)`        | Part of `DailyStats` |
| Sleep            | `get_sleep_data(date)`         | `SleepRecord`        |
| Body Composition | `get_body_composition(date)`   | `BodyComposition`    |
| Stress           | `get_stress_data(date)`        | Part of `DailyStats` |
| Steps            | `get_steps_data(date)`         | Part of `DailyStats` |

## Rate Limiting

- Garmin Connect has no published API rate limits (unofficial API)
- Be conservative: add delays between requests when fetching many days
- Fetch no more than 30 days of data at once
- Cache fetched data locally to avoid re-fetching

## Error Handling

- **Authentication failure**: Surface clear message — "Check GARMIN_EMAIL and GARMIN_PASSWORD in .env"
- **Rate limiting / 429**: Back off and retry after 60 seconds
- **Missing data**: Individual days may have no data for certain types — return `None`, don't error
- **Connection errors**: Wrap in try/catch, log the error

## Data Flow

```
garmin_client.py  →  data_store.py  →  agent reads JSON  →  summary_store.py
   (raw dicts)        (date-stamped)    (analysis)            (Markdown file)
```

## Testing

- Mock `garminconnect.Garmin` in tests — never hit the real API
- Use fixtures in `conftest.py` that mirror real API response shapes
- Test the client's `fetch_range()` method with mocked API calls
