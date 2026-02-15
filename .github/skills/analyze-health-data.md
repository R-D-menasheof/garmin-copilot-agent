# Skill: Analyze Health Data

## Overview

Vitalis uses an **agent-first** analysis model. The GitHub Copilot agent reads raw Garmin data, the user profile, and previous summaries to produce personalised health insights. The report is written **in Hebrew** (prose and table headers) with **English technical terms** (VO2max, HRV, Body Battery, SpO2, REM, RHR, BMI).

## Analysis Workflow — 4 Phases

### Phase 1 — Context (קריאת הקשר)

**Read the latest summary FIRST** — this grounds the analysis in continuity.

1. List files in `data/summaries/` and read the **most recent** `.md` file
2. Pay special attention to the `context_for_next_run` field — this is what past-you asked you to track
3. Note previous `metrics_snapshot` values — you will compare against them to show trends (↑↓→)
4. Note previous recommendations — did the user follow them? Did the metrics improve?

### Phase 2 — Data (קריאת נתונים)

1. Read `data/profile.yaml` — know the user's goals, injuries, metrics, notes
2. Run `python scripts/extract_metrics.py` — this extracts a structured summary of ALL key metrics from the latest sync. Read its output.
3. If you need deeper detail on specific data types (e.g., day-by-day sleep breakdown, individual activity details), read the relevant JSON files from the latest `data/synced/` folder
4. Read `meta.json` in the sync folder to know which data types are available

### Phase 3 — Report (כתיבת דו"ח)

Generate a comprehensive Hebrew health report and write the summary file **immediately** — do not wait for user input.

The report should be based on the data and context gathered in Phases 1-2. Use best judgment for any missing profile information.

### Phase 4 — Clarify & Update (שאלות למשתמש ועדכון)

**After presenting the report**, ask the user follow-up questions about any missing information or data anomalies:

- If `goals` is empty or contains only placeholder comments → ask: "?מה המטרות שלך (כושר, משקל, שינה, תזונה)"
- If `injuries` is empty → ask: "?יש לך פציעות פעילות או מגבלות"
- If `dietary_preferences` is empty → ask: "?העדפות תזונתיות (צמחוני, צום לסירוגין, ללא גלוטן)"
- If `notes` is empty → ask: "?משהו שחשוב לי לדעת — הרגלי קפאין, אלכוהול, לוח זמנים, טריגרים ללחץ"
- If you see anomalies in the data (e.g., a very short sleep night, unusually high stress day) → ask: "?ב-[date] ראיתי [anomaly] — יש סיבה מיוחדת"

**When the user answers**, do the following:

1. Update `data/profile.yaml` with any new information (goals, injuries, dietary preferences, notes)
2. If the answers materially change the analysis or recommendations → **update the summary file** (`data/summaries/YYYY-MM-DD.md`) with revised insights
3. If the answers only add context without changing the analysis → update profile only, no need to rewrite the summary

## Report Format — Hebrew with English Terms

The report should be **long and detailed**, including:

1. **Daily-level highlights** — not just averages. Flag the best and worst days specifically.
2. **Health science explanations** — for each metric, briefly explain WHY it matters (what physiological process it reflects).
3. **Trend comparison** — compare every metric to the previous summary using ↑↓→ arrows.
4. **Hebrew prose** — all text, section headers, and table headers in Hebrew.
5. **English technical terms** — VO2max, HRV, Body Battery, SpO2, REM, RHR, BMI, WHO stay in English.

### Report Sections

```
# דו"ח בריאות ויטליס — YYYY-MM-DD

**תקופה**: YYYY-MM-DD → YYYY-MM-DD
**פרופיל**: שם, גיל, משקל, VO2max, מכשיר

## סיכום מדדים
(טבלה עם כל המדדים — ערך, השוואה לדו"ח קודם, מגמה)

## כושר (Fitness)
(ניתוח מפורט — פעילויות, נפח אימונים, מגמות, שיאים אישיים)
(למה זה חשוב — הסבר פיזיולוגי קצר)

## שינה (Sleep)
(משך, שלבים, ציון, לילות בעייתיים ספציפיים)
(למה זה חשוב — השפעה על recovery, HRV, ביצועים)

## התאוששות (Recovery)
(Body Battery, HRV, RHR, מתח, נשימה)
(למה זה חשוב — allostatic load, parasympathetic function)

## הרכב גוף (Body Composition)
(משקל, שומן גוף, BMI, מגמות)

## תזונה (Nutrition)
(הידרציה, קלוריות אם זמין, הקשר להעדפות תזונתיות)

## בריאות כללית (General Health)
(SpO2, צעדים, קומות, דקות אינטנסיביות, WHO target)

## המלצות
1. **[שינה/Sleep]** כותרת (P1): פירוט עם מספרים. למה זה חשוב.
2. **[התאוששות/Recovery]** כותרת (P2): פירוט עם מספרים.
...

## הקשר להפעלה הבאה
(מה לעקוב, baselines, שאלות פתוחות)
```

## Analysis Domains — What to Evaluate

### כושר (Fitness)

- Activity volume: frequency, duration, distance
- Training load progression — are they doing more or less than last period?
- Activity type distribution — variety vs. specialisation
- Training readiness scores and distribution (<30 / 30-59 / 60+)
- VO2max trend — improving, stable, or declining?
- Personal records — any recent PRs?
- **Why it matters**: VO2max is the strongest predictor of cardiovascular mortality. Training variety reduces overuse injuries and improves overall adaptation.

### שינה (Sleep)

- Total sleep duration (target: 7-9h for adults)
- Sleep stage distribution (deep: 60-90min, REM: 90+min, light: varies)
- Sleep score trend
- Short nights — flag every night <6h by date
- **Why it matters**: Deep sleep drives physical recovery (tissue repair, growth hormone). REM drives cognitive recovery (memory consolidation, emotional regulation). <7h consistently raises cortisol and impairs glucose metabolism.

### התאוששות (Recovery)

- Body Battery patterns — does it recharge to 80+ overnight?
- HRV trends — higher = better parasympathetic recovery
- Resting heart rate trend — lower = fitter; spikes = overtraining/illness
- Stress levels — average and peaks
- Respiration rate — elevated = possible illness/overtraining
- **Why it matters**: HRV reflects autonomic nervous system balance. Body Battery integrates stress, activity, and sleep into recovery readiness. Chronic under-recovery leads to overtraining syndrome.

### הרכב גוף (Body Composition)

- Weight trend — aligned with goals?
- Body fat percentage trend
- BMI context
- Weigh-in consistency — how often?
- **Why it matters**: Tracking trends (not single readings) reveals whether training and nutrition align with goals.

### תזונה (Nutrition)

- Caloric intake vs expenditure (if data available)
- Hydration levels
- Contextualise with dietary preferences from profile
- **Why it matters**: Recovery requires adequate protein (1.6-2.2g/kg for active individuals) and hydration.

### בריאות כללית (General Health)

- SpO2 readings (normal: 95-100%, flag <94%)
- Steps and active minutes vs. goals
- Floors climbed
- Intensity minutes — WHO recommends 150 moderate or 75 vigorous per week
- **Why it matters**: WHO intensity targets are evidence-based thresholds for reducing all-cause mortality by 20-30%.

## Recommendation Rules

- Write recommendations **in Hebrew** with `[category/English]` prefix tag
- Always reference **specific numbers** from the data
- Compare to established health guidelines where applicable
- Account for the user's goals and injuries from profile
- Each recommendation must include a **brief "why this matters"** (1-2 sentences)
- Prioritise based on impact and achievability
- **Maximum 7 recommendations** per analysis — focus on what matters most
- Use priority 1-5 (1 = critical, 5 = positive reinforcement)
- If a recommendation was given last time AND the metric improved → acknowledge the improvement
- If a recommendation was given last time AND nothing changed → rephrase and escalate priority

## Key Metrics Reference

| Metric             | Good Range                           | Warning             | Critical              |
| ------------------ | ------------------------------------ | ------------------- | --------------------- |
| Resting HR         | 40-65 bpm                            | Sudden spike >5bpm  | Sustained >80         |
| HRV                | Rising or stable (personal baseline) | Sustained drop >20% | —                     |
| Sleep duration     | 7-9h                                 | 6-7h                | <6h sustained         |
| Sleep score        | 70+                                  | 50-70               | <50                   |
| Deep sleep         | 60-90 min                            | <60 min             | <30 min               |
| REM sleep          | 90+ min                              | 60-90 min           | <60 min               |
| Body Battery peak  | Recharges to 80+                     | 60-80               | Never above 60        |
| VO2max             | Improving or stable                  | Dropping            | —                     |
| Training readiness | 50+                                  | 30-50               | <30                   |
| SpO2               | 95-100%                              | 94%                 | <94% flag immediately |
| Stress avg         | <35                                  | 35-50               | >50 sustained         |
| Intensity min/wk   | 150+ WHO equiv                       | 75-150              | <75                   |
| Respiration        | 12-20 brpm                           | 20-25 brpm          | >25 brpm              |
| Weight             | Trending toward goal                 | Stagnant            | Moving away from goal |

## Real Garmin Data Structure Notes

These are the actual JSON structures from the Garmin API (learned from real syncs):

- **`daily_stats.json`**: Flat list of dicts. Key fields: `calendarDate`, `totalSteps`, `restingHeartRate`, `averageStressLevel`, `sleepingSeconds`, `bodyBatteryHighestValue`, `bodyBatteryLowestValue`, `floorsAscended`. Note: `averageSPO2Value` is often 0 here — use `spo2.json` instead.
- **`sleep.json`**: List of dicts with nested `dailySleepDTO`. Sleep stages (`deepSleepSeconds`, `remSleepSeconds`, `lightSleepSeconds`, `awakeSleepSeconds`) and scores (`sleepScoreOverall`) are inside `dailySleepDTO`.
- **`training_readiness.json`**: **List of lists** of dicts, each with a `score` field. Flatten before averaging.
- **`training_status.json`**: List of dicts. VO2max is at `mostRecentVO2Max.generic.vo2MaxPreciseValue`.
- **`weigh_ins.json`**: Dict with `dailyWeightSummaries` list. Weight is in **grams** at `latestWeight.weight` (divide by 1000 for kg).
- **`hrv.json`**: List of dicts with `hrvSummary.lastNightAvg`.
- **`body_battery`** type may fail to sync — use `bodyBatteryHighestValue` / `bodyBatteryLowestValue` from `daily_stats.json` as fallback.
- **Not all devices support all types**: Venu 4 doesn't sync hill_score, endurance_score, max_metrics, body_battery, goals, user_summary, daily_sleep_range.

## Helper Scripts

Instead of writing ad-hoc Python to extract metrics, use the permanent helper scripts:

### Period-wide metrics (`extract_metrics.py`)

```
python scripts/extract_metrics.py            # Latest sync
python scripts/extract_metrics.py --json     # JSON output
python scripts/extract_metrics.py --folder 2026-01-19_to_2026-02-15
```

Outputs a structured report covering all metric categories. Use as the foundation for analysis.

### Day-level comparison (`compare_days.py`)

```
python scripts/compare_days.py 2026-02-14                    # Single day
python scripts/compare_days.py 2026-02-13 2026-02-14          # Compare days
python scripts/compare_days.py 2026-02-13 2026-02-14 --json   # JSON output
```

Extracts daily stats, sleep, HRV, activities, training readiness, and stress for specific dates. Use when you need to zoom into individual days or compare day-over-day changes.

**Never create temporary ad-hoc Python scripts** — if a script is needed more than once, make it permanent and create a skill for it.

## Important Notes

- **Be honest but constructive** — flag problems but always suggest solutions
- **Don't over-alarm** — one bad night of sleep isn't a crisis, but a pattern is
- **Look for patterns** over single data points — trends matter more than daily values
- **Account for context** — a high-stress day after a hard workout is expected
- **Respect the profile** — if the user has knee issues, don't push running volume
- **Compare to previous analysis** — always show whether metrics improved or declined
- **Write in Hebrew** — prose and headers in Hebrew, technical terms in English
