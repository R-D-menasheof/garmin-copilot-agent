"""Shared test fixtures for the Vitalis API test suite."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/vitalis is importable in API tests
_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root / "api"))
