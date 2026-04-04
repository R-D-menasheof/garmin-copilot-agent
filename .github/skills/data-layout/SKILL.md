---
name: data-layout
description: "Vitalis data directory structure. File formats, folder conventions, actual Garmin JSON structures (daily_stats, sleep, HRV, training_readiness, weigh_ins, etc.). Use when: reading raw data, understanding file structure, locating data files."
---

# Skill: Data Layout

## Overview

All health data lives under the `data/` directory. This skill describes the folder structure and file formats, including the actual JSON structures returned by the Garmin API.

## Directory Structure

```
data/
├── profile.yaml               # User profile (manual + auto-synced)
├── .garmin_tokens/             # OAuth tokens (NEVER read these)
├── synced/                     # Synced Garmin data
│   ├── YYYY-MM-DD_to_YYYY-MM-DD/  # One folder per sync run
│   │   ├── meta.json           # Sync metadata
│   │   ├── daily_stats.json    # Per-day summary stats
│   │   ├── sleep.json          # Sleep data with stages
│   │   ├── activities.json     # Activities in date range
│   │   ├── heart_rate.json     # Heart rate data
│   │   ├── hrv.json            # Heart rate variability
│   │   ├── stress.json         # Stress data
│   │   ├── all_day_stress.json # All-day stress timeline
│   │   ├── training_readiness.json  # Training readiness scores
│   │   ├── training_status.json     # Training status + VO2max
│   │   ├── body_composition.json    # Body composition
│   │   ├── weigh_ins.json      # Weight measurements
│   │   ├── respiration.json    # Respiration data
│   │   ├── spo2.json           # Blood oxygen (SpO2)
│   │   ├── rhr.json            # Resting heart rate
│   │   ├── intensity_minutes.json   # Weekly intensity minutes
│   │   ├── floors.json         # Floors climbed
│   │   ├── steps.json          # Per-day steps
│   │   ├── daily_steps_range.json   # Steps range data
│   │   ├── hydration.json      # Daily hydration
│   │   ├── devices.json        # Connected devices
│   │   └── personal_records.json    # Personal records
│   └── (older sync folders...)
├── summaries/                  # Agent analysis summaries (Hebrew markdown)
│   ├── 2026-02-15.md
│   └── (older summaries...)
├── uploads/                    # Manual CSV uploads
└── samples/                    # Dev sample data
```

## meta.json Format

```json
{
  "synced_at": "2026-02-15T00:39:58.958955",
  "start_date": "2026-01-19",
  "end_date": "2026-02-15",
  "data_types": ["activities", "daily_stats", "sleep", ...],
  "num_data_types": 21
}
```

## Actual Garmin JSON Structures

These are the real structures from the Garmin Connect API, documented from actual syncs:

### daily_stats.json

Flat list of per-day dicts:

```json
{
  "calendarDate": "2026-02-10",
  "totalSteps": 8500,
  "restingHeartRate": 62,
  "averageStressLevel": 34,
  "sleepingSeconds": 22680,
  "bodyBatteryHighestValue": 56,
  "bodyBatteryLowestValue": 5,
  "floorsAscended": 5.0,
  "averageSPO2Value": 0
}
```

**Note**: `averageSPO2Value` is frequently 0 in daily_stats. Always use `spo2.json` for SpO2 data.

### sleep.json

List of dicts with **nested `dailySleepDTO`** — the sleep data is inside this nested object:

```json
{
  "dailySleepDTO": {
    "calendarDate": "2026-02-10",
    "sleepScoreOverall": 74,
    "deepSleepSeconds": 5340,
    "remSleepSeconds": 4440,
    "lightSleepSeconds": 12840,
    "awakeSleepSeconds": 1080,
    "sleepTimeSeconds": 23700
  },
  "remSleepData": [...],
  "sleepLevels": [...],
  "sleepHeartRate": [...],
  "sleepStress": [...],
  "sleepBodyBattery": [...]
}
```

**Warning**: The top-level dict does NOT have `calendarDate` or `sleepTimeSeconds` directly — they are inside `dailySleepDTO`.

### training_readiness.json

**List of lists** of dicts. Must be flattened:

```json
[
  [{"score": 56, "level": "MODERATE", ...}, {"score": 72, ...}],
  [{"score": 45, ...}]
]
```

### training_status.json

List of dicts. VO2max is deeply nested:

```json
{
  "mostRecentVO2Max": {
    "generic": {
      "vo2MaxPreciseValue": 36.3,
      "vo2MaxValue": 36.0,
      "calendarDate": "2026-01-16"
    }
  }
}
```

### weigh_ins.json

Dict (not list) with `dailyWeightSummaries`. Weight is in **grams**:

```json
{
  "dailyWeightSummaries": [
    {
      "summaryDate": "2026-02-01",
      "latestWeight": {
        "weight": 112000
      }
    }
  ]
}
```

Divide by 1000 for kg. If value < 500, it's already in kg.

### hrv.json

List of dicts with nested `hrvSummary`:

```json
{
  "hrvSummary": {
    "calendarDate": "2026-02-10",
    "lastNightAvg": 30,
    "weeklyAvg": 29,
    "lastNight5MinHigh": 45
  }
}
```

### spo2.json

List of dicts:

```json
{
  "calendarDate": "2026-02-10",
  "averageSPO2": 96,
  "lowestSPO2": 92,
  "latestSPO2": 97
}
```

**Note**: Field may be `averageSPO2` or `averageSpO2` (case varies).

### intensity_minutes.json

List of weekly summaries:

```json
{
  "calendarDate": "2026-02-10",
  "weeklyModerate": 99,
  "weeklyVigorous": 89
}
```

WHO target: 150 equivalent minutes (moderate + 2 × vigorous).

### activities.json

List of activities with nested `activityType`:

```json
{
  "activityType": { "typeKey": "lap_swimming" },
  "duration": 1800,
  "calories": 300,
  "distance": 750.0,
  "startTimeLocal": "2026-02-10 07:30:00"
}
```

### respiration.json

List of dicts:

```json
{
  "calendarDate": "2026-02-10",
  "avgWakingRespirationValue": 15.7,
  "avgSleepingRespirationValue": 14.2
}
```

### personal_records.json

List of dicts with type IDs (not always human-readable names):

```json
{ "typeId": 12, "value": 17201.0, "prStartTimeGMTFormatted": "?" }
```

## Device Compatibility Notes

Not all Garmin devices support all data types. From syncing with Venu 4 - 45mm:

- **Did NOT sync** (7 types): `hill_score`, `endurance_score`, `max_metrics`, `body_battery`, `goals`, `user_summary`, `daily_sleep_range`
- **Did sync** (21 types): All others listed above
- **Workaround**: Body Battery data is available via `bodyBatteryHighestValue` / `bodyBatteryLowestValue` in `daily_stats.json` even when the dedicated `body_battery` endpoint fails

## Helper Script

Use `scripts/extract_metrics.py` to get a structured summary of all metrics from any sync folder:

```
python scripts/extract_metrics.py            # Latest sync
python scripts/extract_metrics.py --json     # JSON output
python scripts/extract_metrics.py --folder YYYY-MM-DD_to_YYYY-MM-DD
```

## Key Rules

- **Never modify** files in `data/synced/` — they are immutable records
- **Never read** `.garmin_tokens/` — OAuth secrets
- **Sync folders are never overwritten** — each sync creates a new folder
- **Multiple syncs for overlapping dates are OK** — latest sync has freshest data
- **Use `meta.json`** to understand available data before reading individual files
- **Use the helper script** rather than writing ad-hoc extraction code
