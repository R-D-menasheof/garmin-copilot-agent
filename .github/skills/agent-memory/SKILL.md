---
name: agent-memory
description: "Vitalis agent memory protocol. Summary format, vitalis-meta JSON block, context_for_next_run field, memory continuity across sessions. Use when: writing summaries, reading previous analysis, maintaining analysis continuity."
---

# Skill: Agent Memory

## Overview

Vitalis uses a file-based memory system. After every analysis, a dated Markdown summary is written to `data/summaries/YYYY-MM-DD.md`. Before the next analysis, the latest summary is loaded for context continuity. All memory I/O lives in `src/vitalis/summary_store.py` (SSOT).

## File Format

Each summary has two sections:

### 1. Human-Readable (Hebrew Markdown)

- Section headers in Hebrew: `## סיכום מדדים`, `## כושר`, `## שינה`, `## המלצות`, `## הקשר להפעלה הבאה`
- Metrics table with comparison to previous report (↑↓→ arrows)
- Detailed domain analysis with health science explanations
- Recommendations in Hebrew with `[heb/eng]` category tags
- Context for next run with specific baselines and tracking items

### 2. Machine-Readable (`vitalis-meta` JSON block)

- **Always in English** — for programmatic consumption
- Contains: `date`, `period_start`, `period_end`, `metrics_snapshot`, `trends`, `recommendations`, `context_for_next_run`
- `metrics_snapshot` should include all quantitative baselines:
  - `avg_daily_steps`, `avg_sleep_hours`, `avg_sleep_score`, `avg_deep_sleep_min`, `avg_rem_sleep_min`
  - `avg_resting_hr`, `avg_hrv_nightly`, `avg_body_battery_peak`, `bb_days_below_80`
  - `avg_training_readiness`, `avg_stress`, `avg_spo2`, `vo2max`, `weight_kg`
  - `weekly_activities`, `total_activities`, `intensity_minutes_moderate`, `intensity_minutes_vigorous`
  - `avg_respiration`, `avg_floors_per_day`, `short_nights_under_6h`

## Memory Protocol

### Writing (after analysis)

1. Generate the full Hebrew report with all sections
2. Append the `vitalis-meta` JSON block at the bottom
3. Save to `data/summaries/YYYY-MM-DD.md` (today's date)
4. If a file for today exists, overwrite it

### Reading (before analysis) — **This is Phase 1 of the analysis workflow**

1. Read the latest summary in `data/summaries/`
2. Extract the `context_for_next_run` — this tells you what to focus on
3. Extract `metrics_snapshot` — you MUST compare current metrics to these baselines
4. Note previous recommendations — check if user followed them

### Comparing Across Analyses

For every metric in `metrics_snapshot`, compare the current value to the previous value:

- Use `↑` for improvement (direction depends on metric — ↑ steps is good, ↑ RHR is bad)
- Use `↓` for decline
- Use `→` for stable (within ±3% change)
- Include percentage or absolute change

## Context for Next Run — Guidelines

The `context_for_next_run` field is the single most important piece of memory. It should include:

1. **Metric baselines** with specific numbers:
   - "HRV baseline: 29ms, RHR baseline: 64 bpm, sleep avg: 6.3h"
2. **Specific tracking items**:
   - "Did sleep improve toward 7h target?"
   - "Did BB peak recover above 80?"
3. **Open questions**:
   - "Short nights cluster on Saturdays — weekend schedule issue?"
4. **Recommendation follow-up**:
   - "Recommended sleep extension — check if implemented"
5. **Anomalies to watch**:
   - "Feb 13 had 4.3h sleep — one-off or pattern?"
   - "HRV declining: 30→31→30→29→29 — continue monitoring"

**Never write generic context** like "continue monitoring all metrics." Be specific.

## Rules

1. **Never skip the summary step** — it's what gives the agent memory
2. **Never edit summaries manually** — overwrite by re-analyzing
3. **Always load previous context** before analysis — this is Phase 1
4. **Git-track summaries** — they are part of the health record
5. **One summary per day** — overwrite if re-analyzed same day
6. **Include both sections** — Hebrew markdown AND English vitalis-meta JSON
7. **Previous summary drives the analysis** — trends and comparisons require it
