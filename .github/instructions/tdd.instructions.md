---
description: "Test-driven development rules for Vitalis. Every bug fix or feature must start with a failing test. Use when writing or modifying Python code."
applyTo: ["backend/**/*.py", "tests/**/*.py", "scripts/**/*.py", "src/**/*.py"]
---

# Test-Driven Development (TDD)

## Workflow

1. **Red** — Write a failing test FIRST
2. **Green** — Implement minimal code to pass the test
3. **Refactor** — Clean up while keeping tests green

## Rules

- No production code changes without a corresponding test
- Tests live in `tests/` (pytest) and `backend/tests/` (pytest)
- Run `pytest` before committing changes
- Test file naming: `test_<module>.py`
- Use `from __future__ import annotations` in all Python files
- Docstrings on all public functions (Google style)
- Type hints required on all function signatures
- No `print()` — use `logging` if needed
