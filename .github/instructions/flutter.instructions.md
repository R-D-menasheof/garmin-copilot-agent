---
description: "Flutter/Dart coding rules for Vitalis mobile app. Provider state management, Isar DB, TDD with flutter_test, Hebrew UI, English comments. Use when writing or modifying Dart/Flutter code."
applyTo: "mobile/**"
---

# Flutter Development Rules

## Language & Style

- Dart 3.x with null safety
- `snake_case.dart` file names, `PascalCase` class names, `camelCase` methods/variables
- English comments, Hebrew UI strings, English technical terms (VO2max, HRV, BMI)

## Architecture

- **Provider** for state management — all logic in `ChangeNotifier`, never in widgets
- **Isar** for local DB — one collection per data type, register schemas in `main.dart`
- **GoRouter** for navigation
- Services (`services/`) handle external I/O (API, Health Connect, camera, local DB)
- Providers (`providers/`) own state and call services

## Testing (TDD)

- Write test first (RED) → implement (GREEN) → refactor
- Widget tests for every screen using `flutter_test`
- Unit tests for all providers and services
- Mock services with `mockito` — never hit real APIs in tests
- Run `flutter test` before considering work complete

## Offline-First

- All writes go to Isar first, then sync to cloud
- Add `synced: bool` field to Isar models for offline queue
- Handle network errors gracefully — queue for retry, show status to user

## Imports

- Prefer relative imports within `lib/`
- Group: dart → flutter → packages → project
