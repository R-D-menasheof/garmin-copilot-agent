---
name: azure-functions-api
description: "Azure Functions V4 Python API design for Vitalis. Read/Write API endpoints, Blob Storage integration, function-key auth, Pydantic validation, ingestion pipeline triggers. Use when: API endpoints, Azure Functions, Blob Storage, REST API design, backend implementation."
---

# Skill: Azure Functions API

## Overview

The Vitalis API is a set of Azure Functions (V4 Python programming model) that serve as the bridge between the Flutter mobile app, the Azure Blob Storage persistence layer, and the Vitalis External Agent (GHCP).

## API Endpoints

### Read API (`api/functions/read_api.py`)

| Method | Endpoint | Query Params | Response | Consumer |
|--------|----------|-------------|----------|----------|
| GET | `/api/v1/nutrition` | `from`, `to` (YYYY-MM-DD) | `{meals: {date: [MealEntry]}}` | Mobile, External Agent |
| GET | `/api/v1/biometrics` | `from`, `to` (YYYY-MM-DD) | `{biometrics: {date: BiometricsRecord}}` | Mobile, External Agent |
| GET | `/api/v1/combined` | `from`, `to` (YYYY-MM-DD) | `{nutrition: {...}, biometrics: {...}}` | External Agent (weekly) |
| GET | `/api/v1/summary/latest` | — | `{summary: AnalysisSummary \| null}` | Mobile |
| GET | `/api/v1/summary/history` | `limit` (default 4) | `{summaries: [AnalysisSummary]}` | Mobile |
| GET | `/api/v1/recommendations/status` | — | `{statuses: [RecommendationStatus]}` | Mobile (Phase 2) |

### Write API (`api/functions/write_api.py`)

| Method | Endpoint | Body | Response | Consumer |
|--------|----------|------|----------|----------|
| POST | `/api/v1/meals` | `MealEntry` | `{status: "ok", meal: MealEntry}` | Mobile |
| POST | `/api/v1/goals` | `NutritionGoal` | `{status: "ok", goal: NutritionGoal}` | External Agent, Mobile |
| POST | `/api/v1/summary` | `AnalysisSummary` | `{status: "ok", summary: AnalysisSummary}` | External Agent (publish_summary.py) |
| POST | `/api/v1/recommendations/status` | `{rec_id, status}` | `{status: "ok"}` | Mobile (Phase 2) |

### Ingestion API (`api/functions/ingestion.py`)

| Method | Endpoint | Body | Response | Consumer |
|--------|----------|------|----------|----------|
| POST | `/api/v1/analyze-image` | `{image: base64}` | `{meals: [MealEntry]}` | Mobile |
| POST | `/api/v1/analyze-text` | `{text: "אכלתי 2 תפוחים"}` | `{meals: [MealEntry]}` | Mobile |

## Azure Functions V4 Pattern

```python
"""Vitalis API — Azure Functions V4 Python."""

from __future__ import annotations

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
```

### HTTP Trigger Template

```python
@app.route(route="v1/nutrition", methods=["GET"])
def get_nutrition(req: func.HttpRequest) -> func.HttpResponse:
    """Return meals for a date range."""
    from_date = req.params.get("from")
    to_date = req.params.get("to")

    if not from_date or not to_date:
        return func.HttpResponse(
            '{"error": "from and to params required"}',
            status_code=400,
            mimetype="application/json",
        )

    # Parse dates, load from blob store, return JSON
    ...
```

## Auth Pattern

Single API key (function-level key from Azure, or custom key in `.env`):

```python
import os

def verify_api_key(req: func.HttpRequest) -> bool:
    """Check x-api-key header against stored key."""
    expected = os.environ.get("VITALIS_API_KEY", "")
    actual = req.headers.get("x-api-key", "")
    return expected and actual == expected
```

Every endpoint calls `verify_api_key()` first → 401 if invalid.

## Blob Storage Integration

`api/shared/blob_store.py` is the SSOT for all Azure Blob operations. Uses `azure.storage.blob.BlobServiceClient`.

```python
class BlobStore:
    """Azure Blob Storage operations — mirrors data_store.py pattern."""

    def __init__(self, connection_string: str | None = None):
        conn = connection_string or os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        self._client = BlobServiceClient.from_connection_string(conn)
        self._container = self._client.get_container_client("vitalis-data")

    def save_meals(self, date: date, meals: list[MealEntry]) -> None: ...
    def load_meals(self, date: date) -> list[MealEntry]: ...
    def load_meals_range(self, start: date, end: date) -> dict[date, list[MealEntry]]: ...
    def save_goals(self, goal: NutritionGoal) -> None: ...
    def load_goals(self) -> NutritionGoal | None: ...
    def save_biometrics(self, date: date, record: BiometricsRecord) -> None: ...
    def load_biometrics_range(self, start: date, end: date) -> dict[date, BiometricsRecord]: ...
    def load_food_cache(self) -> list[KnownFood]: ...
    def append_food_cache(self, food: KnownFood) -> None: ...
    def load_combined(self, start: date, end: date) -> dict: ...
```

### Blob Path Convention

```
vitalis-data/
├── meals/{YYYY-MM-DD}.json           # list[MealEntry]
├── goals/current.json                # NutritionGoal
├── biometrics/{YYYY-MM-DD}.json      # BiometricsRecord
├── food_cache/known_foods.json       # list[KnownFood]
└── sync_state.json                   # timestamps
```

## Request/Response Models

All models imported from `src/vitalis/models.py` (SSOT). Never define request/response models in the API layer — use the shared Pydantic models directly.

```python
from vitalis.models import MealEntry, NutritionGoal, BiometricsRecord, KnownFood
```

## Error Response Pattern

```python
def error_response(message: str, status_code: int = 400) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json",
    )
```

| Status | Meaning |
|--------|---------|
| 200 | Success (GET) |
| 201 | Created (POST) |
| 400 | Invalid request body or params |
| 401 | Missing or invalid API key |
| 404 | Resource not found |
| 500 | Server error |

## Local Development

```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Create local settings
cp api/local.settings.json.example api/local.settings.json
# Edit: add AZURE_STORAGE_CONNECTION_STRING, VITALIS_API_KEY, AZURE_OPENAI_*

# Start (from api/ folder)
cd api
func start

# Or use Azurite for local blob storage emulation
azurite --silent --location .azurite
```

## Testing Pattern

Mock `BlobServiceClient` and `openai.AzureOpenAI` in all tests:

```python
@pytest.fixture
def mock_blob_store(monkeypatch):
    store = BlobStore.__new__(BlobStore)
    store._data = {}  # in-memory storage
    # ... mock methods
    return store
```

## Project Files

```
api/
├── function_app.py              # Import and register all functions
├── functions/
│   ├── __init__.py
│   ├── read_api.py              # GET endpoints
│   ├── write_api.py             # POST endpoints
│   └── ingestion.py             # Image/text analysis + cascade
├── shared/
│   ├── __init__.py
│   ├── blob_store.py            # SSOT: Azure Blob operations
│   ├── food_lookup.py           # SSOT: food DB queries
│   └── vision.py                # SSOT: Azure OpenAI calls
├── tests/
│   ├── conftest.py              # Shared fixtures (mock_blob_store, etc.)
│   ├── test_blob_store.py
│   ├── test_food_lookup.py
│   ├── test_vision.py
│   ├── test_read_api.py
│   ├── test_write_api.py
│   └── test_ingestion.py
├── requirements.txt
├── host.json
└── local.settings.json
```

### requirements.txt

```
azure-functions
azure-storage-blob
pydantic>=2.0
openai
httpx
rapidfuzz
python-dotenv
```
