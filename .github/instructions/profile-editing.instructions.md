---
description: "Rules for editing data/profile.yaml. Preserve all fields, log changes, never delete data, mark medications as stopped. Use when modifying the user health profile."
applyTo: "data/profile.yaml"
---

# Profile Editing Rules

## DO

- Preserve all existing fields when editing
- Add `health_log` entry (with today's date) for: medication changes, supplement changes, injury updates
- Mark stopped medications with `stopped: YYYY-MM-DD` and `note` — do NOT delete entries
- Use Hebrew for health_log notes
- Validate YAML structure after editing

## DO NOT

- Delete any existing data — only add, update, or mark as stopped
- Edit auto-synced fields: `weight_kg`, `body_fat_pct`, `bmi`, `vo2max`, `fitness_age`, `resting_heart_rate`, `devices`, `last_synced`
- Drop fields accidentally when editing adjacent content
- Use tabs — YAML requires spaces for indentation
