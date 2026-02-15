"""Data store — SSOT for persisting synced Garmin data.

Stores raw Garmin API responses as JSON files in date-stamped folders
under data/synced/. Each sync run creates a folder named
``YYYY-MM-DD_to_YYYY-MM-DD/`` containing one JSON file per data type
plus a ``meta.json`` with sync metadata. Previous sync runs are never
overwritten — the agent can read any historical range.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BASE = _PROJECT_ROOT / "data" / "synced"


class DataStore:
    """Read/write raw Garmin data to date-stamped local folders."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else _DEFAULT_BASE
        self._base.mkdir(parents=True, exist_ok=True)

    # ── Write ──────────────────────────────────────────────────────────

    def save_sync(
        self,
        start_date: date,
        end_date: date,
        data: dict[str, Any],
    ) -> Path:
        """Persist a full sync result to a date-stamped folder.

        Args:
            start_date: First day of the sync range.
            end_date: Last day of the sync range.
            data: Dict mapping data-type names to raw API responses
                  (as returned by ``GarminClient.fetch_all``).

        Returns:
            Path to the created sync folder.
        """
        folder_name = f"{start_date.isoformat()}_to_{end_date.isoformat()}"
        folder = self._base / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        # Write one JSON file per data type
        data_types_saved: list[str] = []
        for key, value in data.items():
            if value is None:
                continue
            # Skip empty lists/dicts
            if isinstance(value, (list, dict)) and not value:
                continue
            self._write_json(folder / f"{key}.json", value)
            data_types_saved.append(key)

        # Write meta.json
        meta = {
            "synced_at": datetime.now().isoformat(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data_types": sorted(data_types_saved),
            "num_data_types": len(data_types_saved),
        }
        self._write_json(folder / "meta.json", meta)

        logger.info(
            "Saved sync %s → %s: %d data types to %s",
            start_date, end_date, len(data_types_saved), folder,
        )
        return folder

    # ── Read ───────────────────────────────────────────────────────────

    def list_syncs(self) -> list[dict[str, Any]]:
        """List all sync runs sorted newest-first.

        Returns:
            List of meta.json dicts, each with an added ``folder`` key.
        """
        syncs: list[dict[str, Any]] = []
        for child in sorted(self._base.iterdir(), reverse=True):
            meta_path = child / "meta.json"
            if child.is_dir() and meta_path.exists():
                meta = self._read_json(meta_path)
                if meta:
                    meta["folder"] = str(child)
                    syncs.append(meta)
        return syncs

    def load_data_type(
        self,
        start_date: date,
        end_date: date,
        data_type: str,
    ) -> Any:
        """Load a single data type from a specific sync folder.

        Args:
            start_date: Sync range start.
            end_date: Sync range end.
            data_type: Name of the data type (e.g. 'daily_stats').

        Returns:
            Parsed JSON data, or ``None`` if not found.
        """
        folder = self._base / f"{start_date.isoformat()}_to_{end_date.isoformat()}"
        path = folder / f"{data_type}.json"
        if not path.exists():
            return None
        return self._read_json(path)

    def load_sync_folder(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Load all data types from a sync folder.

        Returns:
            Dict mapping data-type names to their parsed JSON contents.
            Empty dict if folder doesn't exist.
        """
        folder = self._base / f"{start_date.isoformat()}_to_{end_date.isoformat()}"
        if not folder.exists():
            return {}
        result: dict[str, Any] = {}
        for path in folder.glob("*.json"):
            if path.name == "meta.json":
                continue
            key = path.stem
            data = self._read_json(path)
            if data is not None:
                result[key] = data
        return result

    def load_latest(self) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Load complete data from the latest sync.

        Returns:
            Tuple of (meta_dict, data_dict).  (None, {}) if no syncs.
        """
        syncs = self.list_syncs()
        if not syncs:
            return None, {}
        latest = syncs[0]
        start = date.fromisoformat(latest["start_date"])
        end = date.fromisoformat(latest["end_date"])
        data = self.load_sync_folder(start, end)
        return latest, data

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(
            json.dumps(data, default=str, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return None
