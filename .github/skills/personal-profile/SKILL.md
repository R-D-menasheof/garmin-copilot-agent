---
name: personal-profile
description: "User profile fields, YAML structure, how to use for personalisation. Goals, injuries, medications, supplements, dietary preferences, health log. Use when: reading or updating user profile, personalising recommendations."
---

# Skill: Personal Profile

## Overview

The user profile at `data/profile.yaml` contains both manually entered fields and auto-synced Garmin data. It is the foundation for personalised analysis.

## Fields

### Manual Fields (user fills in)

| Field                 | Type   | Description                                                 |
| --------------------- | ------ | ----------------------------------------------------------- |
| `name`                | string | User's name                                                 |
| `age`                 | number | Age in years (can be decimal, e.g., 36.5)                   |
| `sex`                 | string | Male / Female / Other                                       |
| `height_cm`           | number | Height in centimeters                                       |
| `goals`               | list   | Health and fitness goals                                    |
| `injuries`            | list   | Active injuries or physical limitations                     |
| `dietary_preferences` | list   | e.g., vegetarian, intermittent fasting                      |
| `notes`               | string | Free text — caffeine habits, work schedule, stress triggers |

### Auto-Synced Fields (updated by `scripts/sync.py`)

| Field                | Type   | Source                                             |
| -------------------- | ------ | -------------------------------------------------- |
| `weight_kg`          | number | `body_composition` or `weigh_ins`                  |
| `body_fat_pct`       | number | `body_composition`                                 |
| `bmi`                | number | `body_composition`                                 |
| `vo2max`             | number | `max_metrics` (may be null if not in current sync) |
| `fitness_age`        | number | `max_metrics`                                      |
| `resting_heart_rate` | number | Latest `daily_stats`                               |
| `devices`            | list   | `devices` endpoint                                 |
| `last_synced`        | date   | Auto-set on sync                                   |

**Note**: Many auto-synced fields may be `null` if the Garmin API didn't return them for the sync period. VO2max can be found in `training_status.json` → `mostRecentVO2Max.generic.vo2MaxPreciseValue` even when the `max_metrics` endpoint fails.

## How the Agent Should Use the Profile

1. **Always read before analysis** — know the user's context
2. **Tailor recommendations to goals** — weight loss goals → different advice than performance goals
3. **Account for injuries** — don't suggest activities that aggravate them
4. **Use auto-synced metrics for trend awareness** — these are updated every sync
5. **Respect dietary preferences** — don't suggest foods/supplements that conflict
6. **Never modify the profile directly** — only `scripts/sync.py` updates auto-synced fields; for manual fields, ask the user to edit or update it for them after confirmation

## Interactive Profile Completion — Phase 3 of Analysis

When profile fields are empty or contain placeholders, the agent should **ask the user in chat** before generating the report. This happens in Phase 3 of the analysis workflow (see `analyze-health-data` skill).

### Questions to Ask (Hebrew)

**When `goals` is empty or has placeholder comments:**

```
?מה המטרות שלך בתחום הבריאות והכושר
:לדוגמה
- לרדת במשקל ל-X ק"ג
- לשפר שינה ל-7+ שעות
- לשפר VO2max
- לשחות 1500 מטר ברציפות
- להוריד אחוזי שומן
```

**When `injuries` is empty:**

```
?יש לך פציעות פעילות או מגבלות פיזיות שחשוב לי לדעת
:לדוגמה
- כאבי ברכיים
- בעיות גב תחתון
- דלקת גידים בכתף
```

**When `dietary_preferences` is empty:**

```
?מה ההעדפות התזונתיות שלך
:לדוגמה
- צמחוני / טבעוני
- צום לסירוגין (intermittent fasting)
- ללא גלוטן / ללא לקטוז
- high protein
- אין העדפות מיוחדות
```

**When `notes` is empty:**

```
?יש משהו נוסף שחשוב לי לדעת כדי לתת לך ייעוץ טוב יותר
:לדוגמה
- הרגלי קפאין (כמה כוסות ביום, עד איזו שעה)
- צריכת אלכוהול
- לוח זמנים (עבודה במשמרות, נסיעות)
- טריגרים ללחץ
- תרופות שמשפיעות על דופק/שינה
```

**When there are data anomalies:**

```
?ב-[date] ראיתי [anomaly description] — יש סיבה מיוחדת
:לדוגמה
?ב-13/2 ישנת רק 4.3 שעות — קרה משהו מיוחד
?ב-25/1 ה-Body Battery ירד ל-8 — יום מאוד מאתגר
```

### After Receiving Answers

1. Update `data/profile.yaml` with the user's responses
2. Use the new information to personalise the analysis
3. Reference the user's specific goals in recommendations
4. Adjust training advice for injuries
5. Contextualise nutrition advice to dietary preferences
