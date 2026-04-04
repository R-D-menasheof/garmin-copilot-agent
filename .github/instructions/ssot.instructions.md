---
description: "Single Source of Truth (SSOT) rules for Vitalis. Each module owns one concern. Never duplicate logic. Use when modifying core Python modules."
applyTo: ["backend/app/services/**", "src/vitalis/**"]
---

# Single Source of Truth (SSOT)

Each data concern has **exactly one owning module**. Never duplicate logic.

| Concern                  | SSOT Module                    | What it owns                                  |
| ------------------------ | ------------------------------ | --------------------------------------------- |
| Garmin API interaction   | `src/vitalis/garmin_client.py` | Auth, session, raw data fetching (30+ types)  |
| Raw data persistence     | `src/vitalis/data_store.py`    | Date-stamped folders in `data/synced/`        |
| User profile             | `src/vitalis/profile.py`       | `data/profile.yaml` (manual + auto-synced)    |
| Agent memory (summaries) | `src/vitalis/summary_store.py` | `data/summaries/*.md`                         |
| Medical records          | `src/vitalis/medical_store.py` | `data/medical/` (import, extract, index)      |
| Data shapes              | `src/vitalis/models.py`        | Pydantic models                               |
| Sync CLI                 | `scripts/sync.py`              | Command-line sync with date args              |
| Medical import CLI       | `scripts/import_medical.py`    | Import medical documents                      |
| Metric extraction        | `scripts/extract_metrics.py`   | Structured metric extraction from synced data |
| Day comparison           | `scripts/compare_days.py`      | Day-level metric extraction and comparison    |

## Rules

- If logic exists in one module, do NOT reimplement it in another
- Backend services (`backend/app/services/`) mirror `src/vitalis/` — keep them in sync
- New data concerns get new modules — do NOT extend existing modules beyond their SSOT scope
