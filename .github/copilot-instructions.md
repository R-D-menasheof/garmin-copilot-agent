# Vitalis — Copilot Instructions

## What is Vitalis?

Vitalis is your **personal health & fitness adviser** — a multi-agent system for כושר (fitness), תזונה (nutrition), בריאות (health), sleep, and recovery. It syncs 30+ data types from Garmin Connect, stores them locally, and uses a team of specialized AI agents to analyze, advise, and track health over time.

## Agent Architecture

Vitalis uses a **coordinator + specialist** multi-agent pattern:

```
@vitalis (coordinator) → routes user intent to:
├── health-analyst    — Weekly/daily health reports, trend analysis
├── data-syncer       — Garmin sync, medical document imports
├── profile-manager   — Goals, medications, supplements, health log
├── nutrition-coach   — Calorie targets, macros, supplements, diet advice
├── fitness-coach     — Workout plans, training protocols, VO2max
├── health-consultant — Lab interpretation, sleep protocols, recovery
└── vitalis-dev       — Mobile app & API development (Flutter, Azure Functions)
```

**Agents** live in `.github/agents/`. **Skills** provide domain knowledge in `.github/skills/*/SKILL.md`. **Prompts** enable one-click workflows in `.github/prompts/`. **Instructions** enforce rules via `.github/instructions/`. **Hooks** automate lifecycle events via `.github/hooks/`.

### Key Prompts

| Prompt               | What it does                                              |
| -------------------- | --------------------------------------------------------- |
| `/weekly-review`     | Full weekly analysis: sync → analyze → report → questions |
| `/daily-check`       | Quick daily health check                                  |
| `/sync-garmin`       | Sync latest Garmin data                                   |
| `/compare-days`      | Compare specific days side by side                        |
| `/meal-plan`         | Personalized nutrition advice                             |
| `/training-plan`     | Weekly workout plan                                       |
| `/explain-labs`      | Blood test interpretation                                 |
| `/import-medical`    | Import medical document                                   |
| `/scaffold-mobile`   | Scaffold Flutter app + Azure Functions API                |
| `/implement-feature` | Implement a PRD feature with TDD                          |

## Core Principles

### 1. Agent-First Architecture

Analysis is done by the Copilot agent (you), NOT by code. The code layer handles:

- **Data fetching** — `garmin_client.py` pulls 30+ data types from Garmin Connect
- **Data storage** — `data_store.py` saves raw JSON in date-stamped folders
- **Profile management** — `profile.py` maintains `data/profile.yaml`
- **Memory** — `summary_store.py` persists your analysis summaries

**You** handle:

- Reading and interpreting the raw Garmin data
- Comparing against health guidelines and the user's goals
- Generating personalised recommendations
- Writing summaries with `context_for_next_run` for continuity

### 2. Test-Driven Development (TDD)

**Every bug fix or feature MUST start with a failing test.**

- Write the test FIRST (red) → implement code (green) → refactor (clean)
- No production code changes without a corresponding test
- Tests live in `tests/` (pytest)
- Run `pytest` before committing changes

### 3. Single Source of Truth (SSOT)

Each data concern has **exactly one owning module**. Never duplicate logic.

| Concern                  | SSOT Module                             | What it owns                                                |
| ------------------------ | --------------------------------------- | ----------------------------------------------------------- |
| Garmin API interaction   | `src/vitalis/garmin_client.py`          | Auth, session, raw data fetching (30+ types)                |
| Raw data persistence     | `src/vitalis/data_store.py`             | Date-stamped folders in `data/synced/`                      |
| User profile             | `src/vitalis/profile.py`                | `data/profile.yaml` (manual + auto-synced)                  |
| Agent memory (summaries) | `src/vitalis/summary_store.py`          | `data/summaries/*.md`                                       |
| Medical records          | `src/vitalis/medical_store.py`          | `data/medical/` (import, extract, index)                    |
| Lab trends (app-facing)  | `api/shared/blob_store.py`              | `/api/v1/medical/lab-trends` dataset consumed by mobile app |
| Data shapes              | `src/vitalis/models.py`                 | Pydantic models (AnalysisSummary, etc.)                     |
| Sync CLI                 | `scripts/sync.py`                       | Command-line sync with date args                            |
| Medical import CLI       | `scripts/import_medical.py`             | Import medical documents into Vitalis                       |
| Lab trends write API     | `api/functions/write_api.py`            | Save app-facing lab trend series                            |
| Metric extraction        | `scripts/extract_metrics.py`            | Structured metric extraction from synced data               |
| Day comparison           | `scripts/compare_days.py`               | Day-level metric extraction and comparison                  |
| Cloud data (Blob)        | `api/shared/blob_store.py`              | Azure Blob Storage ops (meals, goals, biometrics)           |
| External food DBs        | `api/shared/food_lookup.py`             | Open Food Facts + USDA + fuzzy match cache                  |
| LLM food analysis        | `api/shared/vision.py`                  | Azure OpenAI vision + NLP food parsing                      |
| Nutrition read CLI       | `scripts/read_nutrition.py`             | External Agent reads combined nutrition data                |
| Goal setting CLI         | `scripts/set_goals.py`                  | External Agent sets weekly nutrition goals                  |
| Summary publishing CLI   | `scripts/publish_summary.py`            | Push summaries (with report_markdown) to API                |
| Rec status read CLI      | `scripts/read_recommendation_status.py` | Agent reads recommendation adoption status                  |
| Timeline event CLI       | `scripts/add_timeline_event.py`         | Agent adds health timeline events                           |
| Training program CLI     | `scripts/set_training.py`               | Agent sets structured training programs                     |
| Training read CLI        | `scripts/read_training.py`              | Agent reads active training program                         |
| Goals read CLI           | `scripts/read_goals.py`                 | Agent reads goal programs + milestones                      |
| Sleep read CLI           | `scripts/read_sleep.py`                 | Agent reads sleep checklist entries                         |

### 4. Agent Memory Protocol

Vitalis builds health records over time using a summary-based memory system:

- **After every analysis**, write a `data/summaries/YYYY-MM-DD.md` file
- **After writing**, publish to mobile app: run `python scripts/publish_summary.py --date YYYY-MM-DD`
- **Before every analysis**, read the latest summary's `context_for_next_run` field
- The `context_for_next_run` is free-text context you should read for continuity
- Each summary contains human-readable Markdown AND a `vitalis-meta` JSON block
- **Never skip the summary step** — it's what gives you memory across sessions

### 5. Analysis Workflow

The analysis workflow is defined in the `health-analyst` agent and the `analyze-health-data` skill. The 4-phase workflow:

1. **Phase 1 — Context**: Read latest summary's `context_for_next_run` for continuity
2. **Phase 2 — Data**: Read profile + run extraction scripts + read medical records
3. **Phase 3 — Report**: Generate Hebrew report immediately, consulting nutrition/fitness/health agents for recommendations
4. **Phase 4 — Clarify & Update**: Ask user follow-up questions, update profile and summary if needed

### 6. Report Language

- **Hebrew prose** — all text, section headers, and table headers in Hebrew
- **English technical terms** — VO2max, HRV, Body Battery, SpO2, REM, RHR, BMI stay in English
- **vitalis-meta JSON block** stays in English (machine-readable)

## Tech Stack

- **Python 3.11+** — type hints required on all function signatures
- **Pydantic** — data models for summaries and memory
- **pytest** — all tests
- **garminconnect** — unofficial Garmin Connect API library (30+ data types)
- **PyYAML** — profile.yaml management
- **python-dotenv** — `.env` credential loading
- **PyMuPDF** — PDF text extraction for medical records
- **BeautifulSoup4** — HTML parsing for medical reports
- **GitHub Copilot** — the analysis engine (you)

## Conventions

### Python

- Use `from __future__ import annotations` for modern type syntax
- Pydantic models live in `src/vitalis/models.py`
- Docstrings on all public functions (Google style)
- No `print()` — use `logging` if needed

### Git

- Commit messages: `type: description` (e.g., `feat: add sleep trend chart`, `fix: csv date parsing`)
- Conventional commit types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`

## Project Structure

```
vitalis/
├── src/vitalis/          # Core Python package (SSOT for models & services)
│   ├── garmin_client.py  # Garmin Connect API (auth, fetch 30+ types)
│   ├── data_store.py     # Save raw JSON to date-stamped folders
│   ├── medical_store.py  # Medical record import, extraction, indexing
│   ├── profile.py        # User profile (YAML) management
│   ├── summary_store.py  # Agent memory — read/write summaries
│   └── models.py         # Pydantic models (health + nutrition)
├── mobile/               # Flutter mobile app
│   ├── lib/
│   │   ├── models/       # Dart mirrors of Pydantic models
│   │   ├── providers/    # Provider state management
│   │   ├── screens/      # UI screens
│   │   ├── services/     # API client, Health Connect, Isar, camera
│   │   └── widgets/      # Reusable widgets
│   └── test/             # Flutter tests
├── api/                  # Azure Functions API backend
│   ├── functions/        # HTTP triggers (read_api, write_api, ingestion)
│   ├── shared/           # Business logic (blob_store, food_lookup, vision)
│   └── tests/            # pytest for API
├── scripts/
│   ├── sync.py            # CLI sync (with interactive MFA)
│   ├── import_medical.py  # Import medical documents
│   ├── extract_metrics.py # Structured metric extraction helper
│   ├── compare_days.py    # Day-level comparison helper
│   ├── check_freshness.py # Data freshness check (for hooks)
│   ├── read_nutrition.py  # External Agent reads nutrition data via API
│   └── set_goals.py       # External Agent sets weekly goals via API
├── tests/                 # pytest tests
├── data/
│   ├── profile.yaml       # User profile (gitignored)
│   ├── synced/            # Raw Garmin data (gitignored)
│   ├── medical/           # Medical records (gitignored)
│   ├── summaries/         # Agent analysis memory (gitignored)
│   └── samples/           # Dev sample data
├── .github/
│   ├── copilot-instructions.md  # This file
│   ├── agents/                  # Custom agent definitions
│   │   ├── vitalis.agent.md     # Main coordinator
│   │   ├── health-analyst.agent.md
│   │   ├── data-syncer.agent.md
│   │   ├── profile-manager.agent.md
│   │   ├── nutrition-coach.agent.md
│   │   ├── fitness-coach.agent.md
│   │   ├── health-consultant.agent.md
│   │   └── vitalis-dev.agent.md # Mobile app & API development
│   ├── prompts/                 # One-click workflows
│   ├── skills/                  # Domain knowledge (*/SKILL.md)
│   ├── instructions/            # Always-on rules (*.instructions.md)
│   └── hooks/                   # Lifecycle automation
├── pyproject.toml         # Package config + dependencies
├── .env.example           # Credential template
└── data/profile.example.yaml  # Profile template
```

## Skills

Agent skills live in `.github/skills/*/SKILL.md`. They are loaded on-demand based on their `description` field:

- `analyze-health-data` — Full analysis workflow, metrics, domains, recommendations
- `fetch-garmin-data` — How to sync data, all 30+ data types, CLI usage
- `write-summary` — Summary format, writing rules, memory protocol
- `compare-days` — Day-level comparison script usage and output fields
- `personal-profile` — Profile fields, how to use for personalisation
- `data-layout` — File/folder structure, how to find and read data
- `agent-memory` — Summary format and memory protocol (detailed)
- `health-recommendations` — Recommendation categories and priority scale
- `medical-records` — Medical record management, lab reference ranges, cross-referencing
- `garmin-csv-analysis` — CSV parsing rules (for manual uploads)
- `vitalis-mobile-arch` — System architecture (Flutter ↔ Azure Functions ↔ Blob Storage)
- `flutter-patterns` — Provider, Isar, GoRouter, widget testing, Hebrew RTL
- `azure-functions-api` — V4 Python API, Read/Write endpoints, Blob Storage
- `nutrition-data-pipeline` — Food lookup cascade (cache → OFF → USDA → LLM)
- `health-connect-integration` — Android Health Connect data types and sync
