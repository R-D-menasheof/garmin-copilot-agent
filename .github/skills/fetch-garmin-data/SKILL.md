---
name: fetch-garmin-data
description: "How to sync Garmin Connect data. 30+ data types, CLI usage (sync.py), MFA handling, data storage format. Use when: syncing data, understanding available data types, troubleshooting sync issues."
---

# Skill: Fetch Garmin Data

## Overview

Vitalis can pull 30+ data types from Garmin Connect using `src/vitalis/garmin_client.py`. Data is fetched via the `garminconnect` Python library and saved as raw JSON in date-stamped folders under `data/synced/`.

## How to Sync

### CLI

```bash
# From project root (activate your venv first)
python scripts/sync.py --days 7       # Last 7 days
python scripts/sync.py --today        # Today only
python scripts/sync.py --from 2026-01-01 --to 2026-01-31  # Date range
```

On first run, Garmin may require MFA — the script will prompt you
to enter the verification code sent to your email.

### 429 Workaround — Browser Auth

Since March 2026, Garmin is blocking programmatic SSO login via Cloudflare (returns 429 for all garth/garminconnect users globally). Browser login still works. Use the Playwright-based workaround:

```bash
# One-time setup
pip install playwright requests-oauthlib
playwright install chromium

# Run browser auth — opens Chromium, you login manually
python scripts/browser_auth.py

# Then sync normally — uses saved tokens, no SSO login needed
python scripts/sync.py --days 14
```

The browser auth script saves OAuth tokens to `data/.garmin_tokens/`. `sync.py` picks them up automatically (Phase 1 token-based login). Tokens typically last until they expire or Garmin revokes them.

## Available Data Types (30+)

### Per-Day Data (fetched for each day in the range)

| Key                  | Garmin Method                      | Description                                           |
| -------------------- | ---------------------------------- | ----------------------------------------------------- |
| `daily_stats`        | `get_stats(date)`                  | Steps, calories, active minutes, floors, body battery |
| `heart_rate`         | `get_heart_rates(date)`            | HR zones, resting HR, HR timeline                     |
| `sleep`              | `get_sleep_data(date)`             | Sleep stages, duration, sleep score                   |
| `body_composition`   | `get_body_composition(date)`       | Weight, body fat, BMI, muscle mass                    |
| `stress`             | `get_stress_data(date)`            | Stress level summary                                  |
| `steps`              | `get_steps_data(date)`             | Detailed step data with timestamps                    |
| `respiration`        | `get_respiration_data(date)`       | Breathing rate throughout the day                     |
| `spo2`               | `get_spo2_data(date)`              | Blood oxygen saturation                               |
| `rhr`                | `get_rhr_day(date)`                | Resting heart rate detail                             |
| `hrv`                | `get_hrv_data(date)`               | Heart rate variability                                |
| `training_readiness` | `get_training_readiness(date)`     | Training readiness score and factors                  |
| `training_status`    | `get_training_status(date)`        | Training load, status classification                  |
| `hydration`          | `get_hydration_data(date)`         | Daily water intake                                    |
| `floors`             | `get_floors(date)`                 | Floors climbed detail                                 |
| `intensity_minutes`  | `get_intensity_minutes_data(date)` | Moderate + vigorous minutes                           |
| `hill_score`         | `get_hill_score(date)`             | Hill/climb performance score                          |
| `endurance_score`    | `get_endurance_score(date)`        | Endurance performance score                           |
| `all_day_stress`     | `get_all_day_stress(date)`         | Detailed stress timeline                              |

### Range Data (fetched once for the full range)

| Key                 | Garmin Method                        | Description             |
| ------------------- | ------------------------------------ | ----------------------- |
| `activities`        | `get_activities_by_date(start, end)` | All activities in range |
| `weigh_ins`         | `get_weigh_ins(start, end)`          | Weight measurements     |
| `daily_steps_range` | `get_daily_steps(start, end)`        | Daily step totals       |
| `daily_sleep_range` | `get_daily_sleep(start, end)`        | Daily sleep totals      |

### Snapshot Data (fetched once per sync)

| Key                | Garmin Method           | Description              |
| ------------------ | ----------------------- | ------------------------ |
| `max_metrics`      | `get_max_metrics(date)` | VO2max, fitness age      |
| `personal_records` | `get_personal_record()` | All-time personal bests  |
| `body_battery`     | `get_body_battery()`    | Current body battery     |
| `devices`          | `get_devices()`         | Connected Garmin devices |
| `goals`            | `get_goals()`           | Active fitness goals     |
| `user_summary`     | `get_user_summary()`    | User overview data       |

## Data Storage

After fetch, all data is saved to:

```
data/synced/YYYY-MM-DD_to_YYYY-MM-DD/
├── meta.json
├── daily_stats.json
├── sleep.json
├── ...
```

Each data type gets its own JSON file containing raw API responses. Empty responses are not saved.

## Error Handling

- Each data type fetch is wrapped in `try/except` — one failure doesn't block others
- Not all Garmin devices support all data types (e.g., HRV requires newer watches)
- Rate limiting: be conservative, don't sync more than 90 days at once
- Auth tokens are cached in `data/.garmin_tokens/` — usually no password needed after first login

## After Syncing

1. Check `meta.json` to see which data types were successfully fetched
2. Profile auto-updated with latest weight, VO2max, RHR from Garmin
3. Data is ready for the agent to read and analyse
