---
name: compare-days
description: "Day-level comparison using scripts/compare_days.py. Extracts daily stats, sleep, HRV, activities, training readiness, stress for specific dates. Use when: comparing specific days, investigating anomalies, day-over-day changes."
---

# Skill: Compare Days

## Overview

The `scripts/compare_days.py` script extracts and compares day-level health metrics for **specific dates** from synced Garmin data. It pulls from multiple data files (daily stats, sleep, HRV, activities, training readiness, stress) and presents them in a consolidated per-day view.

**Use this script instead of writing ad-hoc Python** whenever the agent needs to compare specific days or zoom in on individual dates.

## When to Use

- User asks "how was my day yesterday?" or "compare Thursday and Friday"
- Agent needs to investigate a specific anomaly on a known date
- Agent needs day-level granularity beyond what `extract_metrics.py` provides (which gives period-wide averages)
- Comparing recovery after a hard workout vs. rest day
- Investigating a short sleep night or high stress day

## When NOT to Use

- Period-wide analysis → use `extract_metrics.py` instead
- You need to read raw JSON for a field not covered by `compare_days.py` → read the JSON directly

## CLI Usage

```bash
# Single day
python scripts/compare_days.py 2026-02-14

# Compare multiple days
python scripts/compare_days.py 2026-02-13 2026-02-14

# JSON output (for structured parsing)
python scripts/compare_days.py 2026-02-13 2026-02-14 --json

# Specify sync folder (default: latest)
python scripts/compare_days.py 2026-02-14 --folder 2026-01-19_to_2026-02-15
```

## Output Fields

For each date, the script extracts:

### Daily Stats (from `daily_stats.json`)

- Steps, calories (total + active), resting HR
- Stress (avg + max), Body Battery (high + low)
- Floors climbed, distance

### Sleep (from `sleep.json`)

- Duration (hours), sleep score
- Stage breakdown: deep, REM, light, awake (minutes)
- SpO2 average during sleep

### HRV (from `hrv.json`)

- Nightly average, status
- Baseline values

### Activities (from `activities.json`)

- Type, duration, calories, distance
- Average + max heart rate

### Training Readiness (from `training_readiness.json`)

- Score and level

### Stress Detail (from `stress.json`)

- Overall score, rest score
- Stress distribution percentages (low/medium/high)

## Notes

- Dates must be within the sync folder's date range
- If a data type is missing for a date, it's simply omitted from output
- Sleep data uses `dailySleepDTO` (the nested structure) — the `calendarDate` in sleep refers to the night **ending** on that date
- The `--json` flag is useful when the agent needs to parse the output programmatically
- Training readiness data may be nested (list of lists) — the script handles this automatically
