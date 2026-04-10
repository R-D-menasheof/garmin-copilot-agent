---
name: write-summary
description: "Summary file format, writing rules, vitalis-meta JSON block structure, fields, context_for_next_run guidelines. Use when: writing analysis summaries to data/summaries/."
---

# Skill: Write Summary

## Overview

After every analysis, the agent writes a dated Markdown summary to `data/summaries/YYYY-MM-DD.md`. This summary serves as the agent's **memory** — before every future analysis, the latest summary is read for continuity. The report is written **in Hebrew** (prose) with **English technical terms**.

## When to Write a Summary

- After completing a health analysis (see `analyze-health-data` skill)
- When the user explicitly asks for a summary or report
- After a significant sync with new data covering multiple days

## Summary File Format

Each summary file has two sections:

### 1. Human-Readable Markdown (Hebrew)

```markdown
# דו"ח בריאות ויטליס — 2026-02-15

**תקופה**: 2026-02-08 → 2026-02-15
**פרופיל**: רועי, גיל 36.5, 112 ק"ג, VO2max 36.3, Venu 4

## סיכום מדדים

| מדד                | ערך        | דו"ח קודם | מגמה               |
| ------------------ | ---------- | --------- | ------------------ |
| צעדים ביום (ממוצע) | 9,162      | 8,493     | ↑ +8%              |
| שינה (ממוצע)       | 6.3 שעות   | 6.0 שעות  | ↑ +18 דקות         |
| ציון שינה          | 74         | 71        | ↑ +3               |
| שינה עמוקה         | 89 דק'     | —         | —                  |
| REM                | 74 דק'     | —         | ⚠️ מתחת ל-90       |
| RHR ממוצע          | 64 bpm     | 63        | → יציב             |
| HRV (לילי)         | 29 ms      | —         | ⚠️ נמוך, ירידה קלה |
| Body Battery שיא   | 56         | 48        | ↑ +8 אבל עדיין ⚠️  |
| BB לא עלה מעל 80   | 27/27 ימים | —         | ⚠️ כרוני           |
| Training Readiness | 58         | —         | בינוני             |
| מתח ממוצע          | 34         | 33        | → יציב             |
| SpO2               | 96.2%      | —         | ✅ תקין            |
| VO2max             | 36.3       | —         | סביר               |

## כושר (Fitness)

פירוט מלא של פעילויות, נפח אימונים, מגמות...
הסבר למה VO2max חשוב — ניבוי חזק ביותר לתמותה קרדיווסקולרית.
ימים הטובים ביותר: [תאריכים ספציפיים]

## שינה (Sleep)

ניתוח מפורט: ממוצע, ימים בעייתיים, שלבי שינה...
למה Deep sleep חשוב — תיקון רקמות, הורמון גדילה.
לילות קצרים: 25/1 (5.6h), 1/2 (4.9h), ...

## התאוששות (Recovery)

Body Battery, HRV, RHR, מתח, נשימה...
למה HRV חשוב — מאזן מערכת העצבים האוטונומית.

## הרכב גוף (Body Composition)

משקל, מגמות, תדירות שקילות...

## תזונה (Nutrition)

הידרציה, קלוריות, העדפות...

## בריאות כללית (General Health)

SpO2, צעדים, קומות, דקות אינטנסיביות...

## המלצות

1. **[שינה/Sleep]** הארכת שינה ל-7+ שעות (P1): ממוצע 6.3 שעות עם 6 לילות מתחת ל-6 שעות. שינה מספקת היא המנוף המשמעותי ביותר לשיפור כל מדדי ההתאוששות.
2. **[התאוששות/Recovery]** טיפול בגירעון Body Battery כרוני (P1): ...
   ...

## הקשר להפעלה הבאה

(מה לעקוב, baselines, שאלות פתוחות)
```

### 2. Machine-Readable Block (English)

The `vitalis-meta` JSON block stays **in English** — it's machine-readable for code consumption.

````markdown
---

<!-- machine-readable block — do not edit -->

```vitalis-meta
{
  "date": "2026-02-15",
  "period_start": "2026-02-08",
  "period_end": "2026-02-15",
  "metrics_snapshot": {
    "avg_daily_steps": 9162,
    "avg_sleep_hours": 6.3,
    "avg_sleep_score": 74,
    "avg_deep_sleep_min": 89,
    "avg_rem_sleep_min": 74,
    "avg_resting_hr": 64,
    "avg_hrv_nightly": 29,
    "avg_body_battery_peak": 56,
    "bb_days_below_80": 27,
    "avg_training_readiness": 58,
    "avg_stress": 34,
    "avg_spo2": 96.2,
    "vo2max": 36.3,
    "weight_kg": 112.0,
    "weekly_activities": 4.8,
    "total_activities": 19,
    "intensity_minutes_moderate": 99,
    "intensity_minutes_vigorous": 89,
    "avg_respiration": 15.7
  },
  "trends": [...],
  "recommendations": [...],
  "context_for_next_run": "...",
  "report_markdown": "",
  "nudge_rules": [
    {"condition": "sleep_hours < 6", "message_he": "לילה קצר — היום יום קל, תעדיף הליכה", "category": "recovery", "priority": 1},
    {"condition": "resting_hr > 70", "message_he": "דופק מנוחה גבוה — שקול יום מנוחה", "category": "recovery", "priority": 2},
    {"condition": "steps < 3000", "message_he": "מעט תנועה היום — נסה הליכה קצרה", "category": "fitness", "priority": 3}
  ],
  "correlations": [
    {"metric_a": "avg_sleep_hours", "metric_b": "avg_hrv_nightly", "relationship": "positive", "description_he": "HRV גבוה ב-35% אחרי 7+ שעות שינה", "evidence": "4 weeks data", "confidence": 0.85, "discovered_date": "2026-04-08"}
  ]
}
```
````

## Writing Rules

1. **Always include both sections** — Hebrew human-readable AND English vitalis-meta
2. **Use today's date** for the filename (`YYYY-MM-DD.md`)
3. **Overwrite if exists** — only one summary per day
4. **Include profile context** in the header (name, age, weight, VO2max, device)
5. **Reference specific numbers** — never be vague. Use exact values and dates.
6. **Include daily-level highlights** — flag specific best/worst days, not just averages
7. **Each recommendation must explain WHY** — 1-2 sentences of health science
8. **Compare to previous summary** — every metric should show ↑↓→ vs last report
9. **Recommendations in vitalis-meta must be in Hebrew** — `title` and `detail` fields in the JSON `recommendations` array must be Hebrew text (matching the report). Only `category` stays English.
10. **Context for next run** must include:
   - Metric baselines (e.g., "HRV baseline 29ms", "RHR baseline 64 bpm")
   - Specific things to track (e.g., "Did sleep improve toward 7h?")
   - Open questions (e.g., "Short nights cluster on weekends — schedule issue?")
   - Previous recommendations that were followed or ignored
10. **Keep recommendations to 3-7 items** — focus on highest impact
11. **Priority 1-5** (1 = critical, 5 = positive reinforcement)
12. **Hebrew prose** with English technical terms (VO2max, HRV, BB, SpO2, REM, RHR, BMI)
13. **Long and detailed** — the report should be comprehensive, include explanations, not a brief summary
14. **Publish to mobile app** — after saving the summary, run `python scripts/publish_summary.py --date YYYY-MM-DD` to push it to the API. The script reads the raw `.md` file and includes it as `report_markdown` in the API payload so the mobile app can render the full Hebrew report.
15. **Write 3-5 nudge rules** in the `nudge_rules` array — condition-based rules the mobile app evaluates daily against Health Connect biometrics:
    - **Condition format**: `metric_name operator value` (e.g., `sleep_hours < 7`, `resting_hr > 66`). Operators: `<`, `>`, `<=`, `>=`.
    - **Supported metrics**: `sleep_hours` (from sleepSeconds/3600), `resting_hr`, `steps`, `hrv_ms`, `spo2_pct`, `sleep_score`.
    - **Calibrate to user**: set thresholds based on the user's actual baselines from this analysis period, NOT generic values. If avg sleep is 5.9h, a good threshold is `sleep_hours < 7` (not `< 6`). If RHR baseline is 64, use `resting_hr > 62` or `> 66`.
    - **Messages**: Hebrew, actionable, specific — tell the user what to do TODAY.
    - **Priority**: 1-2 = warning (orange card in app), 3-5 = suggestion (blue card).
    - **Coverage**: include at least one rule per domain — sleep, recovery/heart, activity.
    - **Include 1 safety-net rule** with a threshold beyond their normal range (e.g., `resting_hr > 70` when baseline is 64) — fires only on genuinely bad days.
    - **Demo data**: the app's demo mode uses sleep=7.0h, RHR=64, steps=8200, spo2=97. Ensure at least 2 rules fire with demo data so the feature is testable on non-Android devices.
16. **Write 2-3 correlations** in the `correlations` array — cross-domain patterns discovered during analysis (see `correlation-engine` skill). Only include correlations with 4+ data points and confidence > 0.6.
17. **Add timeline events** — after saving the summary, check for milestone events (new personal records, medication changes, medical events, lifestyle changes) and POST each to `/api/v1/timeline` using `scripts/add_timeline_event.py`.

## How to Write Programmatically

Use `SummaryStore` from `src/vitalis/summary_store.py`:

```python
from vitalis.summary_store import SummaryStore

store = SummaryStore()
# save, load_latest, get_context_for_next_run, list_dates
```

## Reading Previous Summaries

```python
context = store.get_context_for_next_run()  # Free-text context string
summary = store.load_latest()               # Full summary object
dates = store.list_dates()                  # All available dates
```
