---
name: correlation-engine
description: "Cross-domain health correlation discovery. Find patterns between sleep, fitness, recovery, nutrition, and body metrics. Use when: generating health reports, looking for data-driven insights, weekly analysis Phase 3."
---

# Skill: Correlation Engine

## Overview

The correlation engine systematically finds cross-domain patterns in the user's health data. Unlike simple metric tracking, correlations reveal **causal or associative relationships** between different health domains.

## When to Run

- During **Phase 3** of the weekly analysis workflow
- After accumulating 4+ weeks of summary data
- When the user asks "what's working?" or "why is X happening?"

## How to Find Correlations

### 1. Compare Metric Pairs Across Summaries

Read the last 4-8 summaries' `metrics_snapshot` and look for:

- **Sleep → Recovery**: Do nights with 7h+ sleep correlate with higher HRV next morning?
- **Swimming → RHR**: Does RHR trend down in weeks with 3+ swim sessions?
- **Stress → Body Battery**: Does avg stress > 35 prevent BB from reaching 80?
- **Sleep → Next-day Steps**: Do short nights (< 6h) correlate with fewer steps?
- **Activity → Sleep Quality**: Do intense training days improve deep sleep?

### 2. Output Format

For each discovered correlation, output:

```json
{
  "metric_a": "avg_sleep_hours",
  "metric_b": "avg_hrv_nightly",
  "relationship": "positive",
  "description_he": "HRV שלך גבוה ב-35% בבקרים אחרי 7+ שעות שינה",
  "evidence": "4 weeks: 7h+ nights → HRV 32 avg, <6h nights → HRV 24 avg",
  "confidence": 0.85,
  "discovered_date": "2026-04-08"
}
```

### 3. Rules

- **Minimum 4 data points** to claim a correlation
- **Confidence scale**: 0.5 = weak pattern, 0.7 = moderate, 0.85+ = strong
- **Report 2-3 correlations per analysis** — quality over quantity
- **Describe in Hebrew** with specific numbers
- **Include evidence** — cite the actual data points
- **Relationship types**: `positive` (both go up together), `negative` (inverse), `threshold` (metric changes above/below a cutoff)

## Report Section

Add a "🔍 תגליות" (Discoveries) section to the Hebrew report:

```markdown
## 🔍 תגליות

1. **שינה → HRV**: ב-4 שבועות, HRV שלך 32 ms ממוצע אחרי לילות 7+h לעומת 24 ms אחרי פחות מ-6h. **שינה היא המנוף הכי חזק ל-HRV.**

2. **שחייה → RHR**: בשבועות עם 3+ אימוני שחייה, RHR ירד ב-2 bpm בממוצע. **ההתמדה בשחייה עובדת.**
```

## Adding to Summary

Include correlations in the `vitalis-meta` JSON block:

```json
"correlations": [
  {
    "metric_a": "avg_sleep_hours",
    "metric_b": "avg_hrv_nightly",
    "relationship": "positive",
    "description_he": "...",
    "evidence": "...",
    "confidence": 0.85,
    "discovered_date": "2026-04-08"
  }
]
```
