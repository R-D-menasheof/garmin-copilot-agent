---
description: "Scaffold the Vitalis mobile app (Flutter) and Azure Functions API backend."
agent: "vitalis-dev"
argument-hint: "Optional: specific component to scaffold (e.g., 'api only', 'flutter only')"
---

Scaffold the Vitalis mobile app and API backend from scratch.

## Steps

1. **Read architecture** — Load the `vitalis-mobile-arch` skill to understand the full system
2. **Create Flutter project** in `mobile/`:
   - `flutter create` with org `com.vitalis`
   - Add dependencies to `pubspec.yaml` (provider, isar, go_router, health, image_picker, http, flutter_secure_storage)
   - Set up `main.dart` with MultiProvider, GoRouter, Isar init, Hebrew locale
   - Create placeholder screens (log_meal, dashboard, history, settings)
   - Create service stubs (api_client, health_connect, local_db, image_service)
   - Write first widget test for dashboard screen
3. **Create Azure Functions project** in `api/`:
   - `func init` with Python v4 model
   - Create `function_app.py`, `host.json`, `requirements.txt`
   - Create `shared/` with `__init__.py`, `blob_store.py`, `food_lookup.py`, `vision.py` stubs
   - Create `functions/` with `read_api.py`, `write_api.py`, `ingestion.py` stubs
   - Write first test for a GET endpoint
4. **Create agent scripts**:
   - `scripts/read_nutrition.py` — CLI stub following `sync.py` pattern
   - `scripts/set_goals.py` — CLI stub following `sync.py` pattern
5. **Verify**: Run `flutter test` and `pytest api/tests/` — at least one test passes in each
