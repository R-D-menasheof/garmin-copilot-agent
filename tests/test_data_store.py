"""Tests for DataStore — date-stamped raw data persistence."""

from datetime import date
import json

import pytest

from vitalis.data_store import DataStore


@pytest.fixture
def store(tmp_path):
    return DataStore(base_dir=tmp_path)


@pytest.fixture
def sample_data():
    return {
        "daily_stats": [{"calendarDate": "2026-02-10", "totalSteps": 9500}],
        "sleep": [{"calendarDate": "2026-02-10", "sleepTimeSeconds": 27000}],
        "activities": [{"activityId": "1", "duration": 1800}],
        "heart_rate": [],
        "body_composition": {},
    }


class TestDataStore:
    def test_save_sync_creates_folder_with_data(self, store, sample_data, tmp_path):
        folder = store.save_sync(date(2026, 2, 10), date(2026, 2, 14), sample_data)
        assert folder.exists()
        assert (folder / "meta.json").exists()
        assert (folder / "daily_stats.json").exists()
        assert (folder / "sleep.json").exists()
        assert (folder / "activities.json").exists()
        # Empty list and empty dict should NOT be saved
        assert not (folder / "heart_rate.json").exists()
        assert not (folder / "body_composition.json").exists()

    def test_meta_json_has_correct_fields(self, store, sample_data):
        store.save_sync(date(2026, 2, 10), date(2026, 2, 14), sample_data)
        meta = store.list_syncs()[0]
        assert meta["start_date"] == "2026-02-10"
        assert meta["end_date"] == "2026-02-14"
        assert "daily_stats" in meta["data_types"]
        assert meta["num_data_types"] == 3  # daily_stats, sleep, activities

    def test_load_data_type(self, store, sample_data):
        store.save_sync(date(2026, 2, 10), date(2026, 2, 14), sample_data)
        loaded = store.load_data_type(date(2026, 2, 10), date(2026, 2, 14), "daily_stats")
        assert loaded[0]["totalSteps"] == 9500

    def test_load_data_type_missing_returns_none(self, store):
        result = store.load_data_type(date(2026, 1, 1), date(2026, 1, 7), "daily_stats")
        assert result is None

    def test_load_sync_folder(self, store, sample_data):
        store.save_sync(date(2026, 2, 10), date(2026, 2, 14), sample_data)
        data = store.load_sync_folder(date(2026, 2, 10), date(2026, 2, 14))
        assert "daily_stats" in data
        assert "sleep" in data
        assert "activities" in data
        assert "meta" not in data  # meta.json excluded from data load

    def test_load_latest(self, store, sample_data):
        store.save_sync(date(2026, 2, 1), date(2026, 2, 7), {"old": [1]})
        store.save_sync(date(2026, 2, 10), date(2026, 2, 14), sample_data)
        meta, data = store.load_latest()
        assert meta is not None
        assert meta["start_date"] == "2026-02-10"
        assert "daily_stats" in data

    def test_load_latest_no_syncs(self, store):
        meta, data = store.load_latest()
        assert meta is None
        assert data == {}

    def test_list_syncs_sorted_newest_first(self, store):
        store.save_sync(date(2026, 1, 1), date(2026, 1, 7), {"a": [1]})
        store.save_sync(date(2026, 2, 1), date(2026, 2, 7), {"b": [2]})
        syncs = store.list_syncs()
        assert len(syncs) == 2
        assert syncs[0]["start_date"] == "2026-02-01"

    def test_multiple_syncs_dont_overwrite(self, store):
        store.save_sync(date(2026, 2, 1), date(2026, 2, 7), {"a": [1]})
        store.save_sync(date(2026, 2, 8), date(2026, 2, 14), {"b": [2]})
        assert len(store.list_syncs()) == 2
        data1 = store.load_sync_folder(date(2026, 2, 1), date(2026, 2, 7))
        data2 = store.load_sync_folder(date(2026, 2, 8), date(2026, 2, 14))
        assert "a" in data1
        assert "b" in data2
