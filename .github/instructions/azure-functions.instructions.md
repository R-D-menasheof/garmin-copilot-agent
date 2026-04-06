---
description: "Azure Functions V4 Python coding rules for Vitalis API. Pydantic models from src/vitalis/models.py (SSOT), pytest TDD, Blob Storage via blob_store.py, logging not print. Use when writing or modifying Azure Functions API code."
applyTo: "api/**"
---

# Azure Functions API Rules

## Python

- Python 3.11+ with `from __future__ import annotations`
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- `logging` module only — no `print()`

## SSOT

- **ALL Pydantic models** live in `src/vitalis/models.py` — never define models in `api/`
- `api/shared/blob_store.py` is the ONLY module that touches Azure Blob Storage
- `api/shared/food_lookup.py` is the ONLY module that queries Open Food Facts / USDA
- `api/shared/vision.py` is the ONLY module that calls Azure OpenAI

## Azure Functions V4

- Use decorator model: `@app.route(route="v1/endpoint", methods=["GET"])`
- Return `func.HttpResponse` with proper status codes and `mimetype="application/json"`
- Validate request bodies with Pydantic: `Model.model_validate_json(req.get_body())`
- Every endpoint calls `verify_api_key(req)` first → 401 if invalid

## Error Responses

```python
{"error": "message"}  # with appropriate HTTP status code
```

| Code | When |
|------|------|
| 200 | Successful GET |
| 201 | Successful POST (created) |
| 400 | Invalid request body or params |
| 401 | Missing or invalid API key |
| 500 | Server error |

## Testing (TDD)

- Write test first (RED) → implement (GREEN) → refactor
- Tests in `api/tests/` using `pytest`
- Mock `BlobServiceClient` and `openai.AzureOpenAI` — never hit real services
- Mock HTTP calls to Open Food Facts / USDA with `httpx` mocking
- Run `pytest api/tests/` before considering work complete
