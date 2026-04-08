---
name: health-recommendations
description: "Recommendation categories, priority scale (P1-P5), formatting rules, maximum 7 recommendations per analysis. Use when: generating health recommendations, prioritizing advice."
---

# Skill: Health Recommendations

## Overview

Generate actionable, personalized health recommendations in **Hebrew** with English category tags. Recommendations are part of the analysis report — see `analyze-health-data` skill for the full workflow.

## Recommendation Format

Each recommendation follows this structure:

```
N. **[category_heb/category_eng]** כותרת בעברית (PN): פירוט עם מספרים ספציפיים.
   למה זה חשוב: הסבר פיזיולוגי קצר (1-2 משפטים).
```

Example:

```
1. **[שינה/Sleep]** הארכת שינה ל-7+ שעות (P1): ממוצע 6.3 שעות עם 6 לילות מתחת ל-6.
   למה זה חשוב: שינה מספקת מאפשרת שחרור הורמון גדילה בשינה עמוקה ועיבוד זיכרונות ב-REM.
```

## Categories

| Category (Eng) | Category (Heb) | Covers                                                 |
| -------------- | -------------- | ------------------------------------------------------ |
| `sleep`        | שינה           | Duration, quality, consistency, stages, score          |
| `fitness`      | כושר           | Training volume, frequency, intensity, variety, VO2max |
| `recovery`     | התאוששות       | Body Battery, HRV, RHR, stress, rest days              |
| `body`         | הרכב גוף       | Weight trends, body fat, BMI, weigh-in consistency     |
| `nutrition`    | תזונה          | Hydration, caloric balance, dietary alignment          |
| `health`       | בריאות         | SpO2, steps, intensity minutes, respiration, general   |

## Priority Scale

| Priority | Meaning                | When to use                                  |
| -------- | ---------------------- | -------------------------------------------- |
| 1        | קריטי (Critical)       | Metric significantly outside healthy range   |
| 2        | חשוב (Important)       | Metric below optimal, action needed          |
| 3        | מומלץ (Suggested)      | Room for improvement                         |
| 4        | לידיעה (Informational) | Awareness, no urgent action                  |
| 5        | חיובי (Positive)       | Reinforce good habits — acknowledge progress |

## Thresholds

### Sleep (שינה)

- **P1**: avg < 6h sustained OR sleep score < 50
- **P2**: avg 6-7h OR sleep score 50-70 OR REM < 60min sustained
- **P3**: avg 7-7.5h (could be better) OR deep < 60min
- **Good**: avg 7-9h, score 70+, deep 60-90min, REM 90+min

### Fitness (כושר)

- **P2**: avg steps < 5,000/day OR no activities in a week
- **P3**: avg steps 5,000-7,000/day OR VO2max declining
- **Good**: avg > 7,000 steps, regular activity mix, VO2max stable/improving

### Recovery (התאוששות)

- **P1**: HRV drop > 30% from baseline sustained
- **P2**: Body Battery peak never above 80 (chronic) OR RHR spike > 5bpm sustained
- **P3**: Body Battery avg peak < 60 OR stress avg > 40
- **Good**: BB recharges to 80+, HRV stable/rising, stress < 35

### Body (הרכב גוף)

- **P2**: avg RHR > 80 bpm (non-athlete)
- **P3**: weight trending away from goal OR no weigh-ins for tracking
- **Good**: weight stable or trending toward goal, regular weigh-ins

### Health (בריאות)

- **P1**: SpO2 < 94% — flag immediately
- **P2**: intensity minutes < 75/week (far below WHO)
- **P3**: intensity minutes 75-150/week OR respiration > 20 brpm
- **Good**: SpO2 95-100%, intensity min 150+, respiration 12-20

## Personalisation Rules

1. **Compare to previous analysis**: Reference improvement or regression explicitly (e.g., "שינה השתפרה מ-6.0 ל-6.3 שעות — המשך כך!")
2. **Don't repeat stale recommendations**: If the same rec was given last time AND the metric hasn't changed, rephrase and consider escalating priority
3. **Prioritise new negative trends**: A newly declining metric gets higher priority than a persistent issue
4. **Account for goals and injuries**: Tailor to what the user cares about (from profile)
5. **Each recommendation must explain WHY**: Brief health science context (1-2 sentences)
6. **Maximum 7 recommendations**: Don't overwhelm — focus on most impactful items
7. **Include at least one P5 (positive)**: Reinforce what's going well — motivation matters
8. **Write in Hebrew**: All recommendation text in Hebrew, with `[heb/eng]` category tag
9. **vitalis-meta JSON must also be in Hebrew**: The `title` and `detail` fields in the machine-readable `recommendations` array must be in **Hebrew** (matching the report prose). Only `category` stays in English for programmatic matching. Example:
   ```json
   {"category": "sleep", "title": "הארכת שינה ל-7+ שעות", "priority": 1, "detail": "ממוצע 5.9 שעות עם 43% לילות קצרים. הייתה 7.2 שעות לפני שבועיים."}
   ```
10. **P5 recommendations are achievements, not tasks**: Write P5 titles as observations/celebrations (e.g., "RHR ירד ל-64 — השחייה עובדת!") — the mobile app displays them separately as achievements, not actionable checkboxes.

## Recommendation Tracking

Each recommendation gets a **stable ID** (SHA-256 hash of `category + title`) so it can be tracked across sessions. The mobile app allows users to mark recommendations as **done**, **snoozed**, or leave them **pending**.

### Tracking Rules

1. **Read adoption status** before writing new recommendations — check `scripts/read_recommendation_status.py` output (Phase 2 feature, skip if script doesn't exist yet)
2. **Adopted + metric improved** → escalate to P5 (positive reinforcement): "המלצה יושמה בהצלחה! [metric] השתפר מ-X ל-Y"
3. **Adopted + no improvement** → rephrase with modified approach, keep same priority or escalate
4. **Snoozed** → remind next time only if metric is still relevant
5. **Ignored (pending for 2+ weeks)** → consider rephrasing or escalating priority
6. **New recommendations** carry forward: if the same `category + title` was given before, reference the history
