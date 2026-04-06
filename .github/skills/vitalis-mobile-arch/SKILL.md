---
name: vitalis-mobile-arch
description: "Vitalis mobile app system architecture. Flutter ↔ Azure Functions ↔ Blob Storage ↔ External Agent data flows, SSOT boundaries, cost strategy ($10/mo), offline-first sync, nutrition cascade pipeline. Use when: architecture questions, system design, data flow, integration planning, cost optimization."
---

# Skill: Vitalis Mobile Architecture

## System Overview

Vitalis mobile is a nutrition + biometrics tracking app that extends the existing Vitalis health agent system. The mobile app captures food intake and wearable data; the existing GHCP agent system acts as the "External Agent" that analyzes trends and sets weekly goals.

## Architecture Diagram

```
┌─────────────────────┐        ┌─────────────────────────────┐
│   Flutter Mobile     │ HTTPS  │  Azure Functions             │
│   (mobile/)          │───────▶│  (Consumption Plan)          │
│                      │        │                              │
│  • Log meals         │        │  Read API (GET)              │
│  • View goals        │        │  ├ /api/v1/nutrition         │
│  • Dashboard         │        │  ├ /api/v1/biometrics        │
│  • Camera capture    │        │  └ /api/v1/combined          │
│  • Health Connect    │        │                              │
│                      │        │  Write API (POST)            │
│  Offline: Isar DB    │        │  ├ /api/v1/meals             │
│  Sync: background +  │        │  ├ /api/v1/goals             │
│    on-app-open       │        │  └ /api/v1/analyze-image     │
└─────────────────────┘        │                              │
                                │  Ingestion Pipeline          │
                                │  (cascade: cache → OFF →     │
                                │   USDA → LLM)               │
                                └──────┬──────────┬────────────┘
                                       │          │
                                       ▼          ▼
                              ┌─────────────┐  ┌──────────────┐
                              │ Azure Blob   │  │ Azure OpenAI │
                              │ Storage      │  │ GPT-4o       │
                              │              │  │              │
                              │ vitalis-data/│  │ • Vision     │
                              │ ├ meals/     │  │ • NLP        │
                              │ ├ goals/     │  │ (fallback    │
                              │ ├ biometrics/│  │  only)       │
                              │ └ food_cache/│  └──────────────┘
                              └──────┬───────┘
                                     │
                                     ▲
                              ┌──────┴───────────────────┐
                              │  Vitalis External Agent    │
                              │  (GHCP agent system)       │
                              │                            │
                              │  scripts/read_nutrition.py  │
                              │  → GET /api/v1/combined     │
                              │                            │
                              │  scripts/set_goals.py       │
                              │  → POST /api/v1/goals       │
                              │                            │
                              │  Weekly: analyze trends,    │
                              │  set calorie/macro targets  │
                              └────────────────────────────┘
```

## Data Flows

### 1. User Logs a Meal (Mobile → Cloud)

```
User input (text/image/selection)
  ↓
POST /api/v1/meals  OR  POST /api/v1/analyze-image
  ↓
Ingestion Pipeline (cascade):
  1. Check food_cache/known_foods.json (fuzzy match, rapidfuzz)
  2. Query Open Food Facts API (Hebrew + English)
  3. Query USDA FoodData Central (English only)
  4. Azure OpenAI GPT-4o (vision for images, NLP for text)
  5. Direct entry bypass (user provides raw macros)
  ↓
Store MealEntry in meals/{date}.json
Cache new food in food_cache/known_foods.json
  ↓
Response: list[MealEntry] with resolved nutritional data
```

### 2. External Agent Weekly Review (Cloud → Agent)

```
scripts/read_nutrition.py --from 2026-03-28 --to 2026-04-04
  ↓
GET /api/v1/combined?from=2026-03-28&to=2026-04-04
  ↓
Returns: {nutrition: {date: [MealEntry]}, biometrics: {date: BiometricsRecord}}
  ↓
health-analyst reads combined data + Garmin synced data
  ↓
Analysis: "HRV dropped + weight up, despite calorie compliance"
  ↓
scripts/set_goals.py --calories 2100 --protein 180 --carbs 220 --fat 65
  ↓
POST /api/v1/goals → updates goals/current.json
  ↓
Mobile app reads updated goals on next open
```

### 3. Health Connect Sync (Wearable → Cloud)

```
Garmin Venu 4 → Health Connect (Android)
  ↓
Flutter `health` package reads:
  • Heart rate, HRV, SpO2, body temp
  • Steps, active calories, exercise sessions
  • Sleep stages (REM, deep, light, awake)
  • Weight, body fat %
  ↓
BiometricsRecord posted to /api/v1/biometrics (via write_api)
  ↓
Stored in biometrics/{date}.json
```

## SSOT Boundaries

| Concern | SSOT Module | Notes |
|---------|-------------|-------|
| ALL Pydantic models | `src/vitalis/models.py` | Nutrition models added alongside existing medical/health models |
| Cloud data (Blob) | `api/shared/blob_store.py` | Mirrors `data_store.py` pattern (date-stamped JSON) |
| External food DBs | `api/shared/food_lookup.py` | Open Food Facts + USDA + fuzzy match |
| LLM food analysis | `api/shared/vision.py` | Azure OpenAI vision + NLP |
| Local Garmin data | `src/vitalis/data_store.py` | Unchanged |
| Profile | `src/vitalis/profile.py` | Unchanged |
| Summaries | `src/vitalis/summary_store.py` | Unchanged |
| Medical records | `src/vitalis/medical_store.py` | Unchanged |

## Blob Storage Structure

```
vitalis-data/                        # Azure Blob container
├── meals/
│   ├── 2026-04-04.json             # [MealEntry, MealEntry, ...]
│   ├── 2026-04-03.json
│   └── ...
├── goals/
│   └── current.json                 # NutritionGoal
├── biometrics/
│   ├── 2026-04-04.json             # BiometricsRecord
│   └── ...
├── food_cache/
│   └── known_foods.json            # [KnownFood, ...] (~50KB for 1000 items)
└── sync_state.json                  # Last sync timestamps
```

This mirrors the existing `data/synced/` local pattern — date-stamped JSON files, one per data type per day.

## Cost Strategy ($10/mo Target)

| Service | Expected Cost | Optimization |
|---------|--------------|--------------|
| Azure Functions (Consumption) | ~$0 | 1M free executions/mo |
| Azure Blob Storage | ~$0.01 | Tiny data volume for single user |
| Azure OpenAI GPT-4o | ~$2-5 | Food cache eliminates repeat LLM calls |
| **Total** | **~$2-5/mo** | Shrinks as food cache grows |

Key cost lever: the food cache. After 1 month of use, ~95% of foods should be cached, reducing LLM calls to near-zero.

## Offline-First Strategy

```
Mobile (Isar DB) ──online──▶ Azure Functions ──▶ Azure Blob
                  ──offline──▶ Queue in Isar (synced=false)
                  ──reconnect──▶ Batch sync queued items
```

- Meals stored locally in Isar with `synced: false` flag
- Background isolate syncs when connectivity returns
- Goals cached locally — always available offline
- Biometrics queued and batch-synced every 4 hours + on app open

## API Auth

Single user, single API key:
- Stored in `.env` (same pattern as Garmin credentials)
- Flutter app stores in `flutter_secure_storage`
- Sent as `x-api-key` header on every request
- HTTPS only (no CORS needed — native app, not browser)
