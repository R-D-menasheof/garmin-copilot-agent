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

### Authentication Flow (garminconnect 0.3.3 / May 2026)

`garminconnect` 0.3.3 ships its own login client (no longer uses `garth.Client` for SSO) with a 5-strategy cascading chain that automatically falls through on 429:

1. `mobile+cffi` — iOS app flow with curl_cffi TLS fingerprint rotation
2. `mobile+requests` — iOS app flow with plain requests
3. `widget+cffi` — SSO embed widget (HTML form flow)
4. `portal+cffi` — Portal web login (Cloudflare-fingerprinted)
5. `portal+requests` — Portal web login (plain requests)

**Expect WARNINGS like `mobile+cffi returned 429: Mobile login returned 429`** — these are NOT fatal. The chain falls through and one of the later strategies will normally succeed (then ask for MFA). Only fail if you see `All login strategies rate limited (429)` after all 5 attempts.

### Token Cache

After a successful MFA login, tokens are saved to `data/.garmin_tokens/garmin_tokens.json` (single file, garminconnect 0.3.3 format). Subsequent `sync.py` runs use the cached tokens — no MFA, no 429 cascade. Tokens auto-refresh via DI refresh token; no manual rotation needed.

If `sync.py` keeps re-prompting for MFA on every run, check that:
- `data/.garmin_tokens/garmin_tokens.json` exists and has size > 0 after the previous run
- The token store directory isn't being wiped between runs (e.g. by OneDrive sync conflicts)
- `garminconnect >= 0.3.3` and `garth >= 0.8.0` are installed (older versions used a different on-disk format and our client looks for both)

### What to do if MFA fails or the chain rate-limits

- **Wait 2-3 hours** before retrying. Garmin's 429 bucket is cumulative per IP and per account — every failed attempt fills it further.
- **Never retry in a loop** — each attempt sends another MFA email and burns a token-exchange slot.
- If sync hangs at the MFA prompt, finish the prompt or Ctrl-C cleanly; killing the terminal mid-prompt sometimes leaves the in-memory MFA session orphaned (you'll need to restart and trigger a new MFA email).

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
- Auth tokens are cached in `data/.garmin_tokens/garmin_tokens.json` — usually no MFA needed after first login

## After Syncing

1. Check `meta.json` to see which data types were successfully fetched
2. Profile auto-updated with latest weight, VO2max, RHR from Garmin
3. Data is ready for the agent to read and analyse
