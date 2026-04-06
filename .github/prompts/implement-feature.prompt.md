---
description: "Implement a specific PRD feature for the Vitalis mobile app using TDD."
agent: "vitalis-dev"
argument-hint: "Feature ID and name, e.g. 'FR-1.1 Search & Database' or 'FR-1.3 Vision'"
---

Implement the requested PRD feature using strict TDD.

## Feature Reference

| ID | Feature | Key Module |
|----|---------|------------|
| FR-1.1 | Search & Database | `api/shared/food_lookup.py` |
| FR-1.2 | Personal History (Recents & Favorites) | `api/shared/blob_store.py` + fuzzy match |
| FR-1.3 | Vision (GPT-4o image analysis) | `api/shared/vision.py` |
| FR-1.4 | Natural Language parsing | `api/shared/vision.py` |
| FR-1.5 | Direct Entry (bypass cascade) | Mobile UI + `api/functions/write_api.py` |
| FR-2 | Health Connect integration | `mobile/lib/services/health_connect.dart` |
| FR-3 | Dual API (Read + Write) | `api/functions/read_api.py` + `write_api.py` |

## TDD Workflow

1. **Read the PRD requirement** — understand what the feature does, inputs, outputs
2. **Read relevant skills** — load the matching skill (nutrition-data-pipeline, azure-functions-api, flutter-patterns, health-connect-integration)
3. **Check existing models** — read `src/vitalis/models.py` to see if needed models exist
4. **Write failing tests (RED)**:
   - Python: add tests to the appropriate `api/tests/test_*.py` or `tests/test_*.py`
   - Dart: add tests to `mobile/test/`
   - Tests should import not-yet-existing functions and assert expected behavior
5. **Run tests** — confirm they fail with ImportError or AssertionError
6. **Implement minimal code (GREEN)** — write just enough to pass the tests
7. **Run tests** — confirm all pass
8. **Refactor** — clean up while keeping tests green
9. **Run full test suite** — `pytest tests/ api/tests/` and `flutter test` — no regressions
