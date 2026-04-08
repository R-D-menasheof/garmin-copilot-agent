---
name: goal-programs
description: "Structured goal programs with milestones for health accountability. Predefined templates for weight loss, VO2max improvement, sleep reset. Use when: creating goal programs, tracking progress, weekly milestone updates."
---

# Skill: Goal Programs

## Overview

Goal programs give structure to health objectives. Instead of vague goals like "lose weight," programs have defined durations, measurable milestones, and weekly agent tracking.

## Predefined Program Templates

### 1. מבצע VO2max 40 (8 weeks)

```json
{
  "name_he": "מבצע VO2max 40",
  "description_he": "שיפור כושר אירובי מ-36 ל-40+ תוך 8 שבועות",
  "duration_weeks": 8,
  "milestones": [
    {"title_he": "שחייה 3x/שבוע", "target_metric": "weekly_swims", "target_value": 3},
    {"title_he": "אימון אינטרוולים 1x/שבוע", "target_metric": "interval_sessions", "target_value": 1},
    {"title_he": "VO2max 38", "target_metric": "vo2max", "target_value": 38},
    {"title_he": "VO2max 40", "target_metric": "vo2max", "target_value": 40}
  ]
}
```

### 2. פרויקט 100 ק"ג (12 weeks)

```json
{
  "name_he": "פרויקט 100 ק\"ג",
  "description_he": "ירידה מ-112 ל-100 ק\"ג תוך 12 שבועות",
  "duration_weeks": 12,
  "milestones": [
    {"title_he": "שקילה שבועית", "target_metric": "weekly_weighins", "target_value": 1},
    {"title_he": "גירעון קלורי 500 kcal/יום", "target_metric": "calorie_deficit", "target_value": 500},
    {"title_he": "חלבון 1.6g/kg/יום", "target_metric": "daily_protein_g", "target_value": 180},
    {"title_he": "משקל 108 ק\"ג", "target_metric": "weight_kg", "target_value": 108},
    {"title_he": "משקל 104 ק\"ג", "target_metric": "weight_kg", "target_value": 104},
    {"title_he": "משקל 100 ק\"ג", "target_metric": "weight_kg", "target_value": 100}
  ]
}
```

### 3. איפוס שינה (2 weeks)

```json
{
  "name_he": "איפוס שינה",
  "description_he": "חזרה ל-7+ שעות שינה ללילה תוך שבועיים",
  "duration_weeks": 2,
  "milestones": [
    {"title_he": "7h שינה 5/7 לילות", "target_metric": "nights_above_7h", "target_value": 5},
    {"title_he": "ציון שינה > 75", "target_metric": "avg_sleep_score", "target_value": 75},
    {"title_he": "BB שיא > 70", "target_metric": "body_battery_peak", "target_value": 70},
    {"title_he": "צ'קליסט שינה 100%", "target_metric": "checklist_compliance", "target_value": 100}
  ]
}
```

## How the Agent Manages Programs

### Creating a Program

When the user asks for a goal program or the agent identifies a clear objective:

1. Select the appropriate template or create a custom one
2. POST to `/api/v1/goals/programs` via `scripts/set_goals.py` (or a new script)
3. Reference the active program in the weekly report

### Weekly Updates

During `/weekly-review` Phase 3:

1. Load active programs from the API
2. Compare current metrics against milestone targets
3. Update `current_value` for each milestone
4. Calculate `progress_pct`
5. Report progress in Hebrew: "פרויקט 100 ק"ג — שבוע 3/12, משקל 112→111 ק"ג"

### Completing a Program

When all milestones are met OR the duration expires:
- Mark `active: false`
- Add a timeline event: category "milestone", severity "positive"
- Celebrate in the report with P5 achievements
