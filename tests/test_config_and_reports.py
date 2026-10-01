"""
Tests for Campus Configuration persistence and Building Report engine.

These tests verify BEHAVIORAL correctness:
- Configuration saves and loads correctly
- 16-building limit is enforced
- Report filtering actually changes underlying data
- Building A ≠ Building B when data differs
- Day ≠ Week aggregation
- No-telemetry buildings are handled without fabrication
- FDI events are correctly counted
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd
import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# ============================================================
# Campus Configuration Tests
# ============================================================

class TestCampusConfiguration:
    """Test the campus_config loader/saver."""

    def setup_method(self):
        """Create a temporary directory for test configs."""
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = Path(self.tmpdir) / "university_layout.yaml"

        # Monkey-patch the module paths for testing
        import dashboard.data.campus_config as cc
        self._orig_dir = cc._CONFIG_DIR
        self._orig_path = cc._CONFIG_PATH
        cc._CONFIG_DIR = Path(self.tmpdir)
        cc._CONFIG_PATH = self.config_path

    def teardown_method(self):
        """Restore original paths and clean up."""
        import dashboard.data.campus_config as cc
        cc._CONFIG_DIR = self._orig_dir
        cc._CONFIG_PATH = self._orig_path
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_layout_when_no_file(self):
        from dashboard.data.campus_config import load_campus_layout
        layout = load_campus_layout()
        assert isinstance(layout, dict)
        assert "university_id" in layout
        assert "buildings" in layout
        assert len(layout["buildings"]) == 0

    def test_save_and_load_roundtrip(self):
        from dashboard.data.campus_config import load_campus_layout, save_campus_layout
        layout = {
            "university_id": "test_uni",
            "university_name": "Test University",
            "campus_id": "test_campus",
            "campus_name": "Test Campus",
            "buildings": [
                {"id": "bldg_a", "name": "Building A", "num_floors": 3},
                {"id": "bldg_b", "name": "Building B", "num_floors": 2},
            ],
        }
        save_campus_layout(layout)
        loaded = load_campus_layout()
        assert loaded["university_id"] == "test_uni"
        assert loaded["university_name"] == "Test University"
        assert len(loaded["buildings"]) == 2
        assert loaded["buildings"][0]["id"] == "bldg_a"
        assert loaded["buildings"][1]["num_floors"] == 2

    def test_16_building_limit_enforced(self):
        from dashboard.data.campus_config import save_campus_layout
        layout = {
            "university_id": "test",
            "buildings": [{"id": f"b{i}", "name": f"B{i}", "num_floors": 1} for i in range(17)],
        }
        with pytest.raises(ValueError, match="17 buildings exceeds"):
            save_campus_layout(layout)

    def test_exactly_16_buildings_allowed(self):
        from dashboard.data.campus_config import save_campus_layout, load_campus_layout
        layout = {
            "university_id": "test",
            "buildings": [{"id": f"b{i}", "name": f"B{i}", "num_floors": 1} for i in range(16)],
        }
        save_campus_layout(layout)
        loaded = load_campus_layout()
        assert len(loaded["buildings"]) == 16

    def test_config_persists_to_disk(self):
        from dashboard.data.campus_config import save_campus_layout
        layout = {
            "university_id": "disk_test",
            "buildings": [{"id": "x", "name": "X", "num_floors": 1}],
        }
        save_campus_layout(layout)
        assert self.config_path.exists()
        raw = yaml.safe_load(open(self.config_path))
        assert raw["university_id"] == "disk_test"


# ============================================================
# Report Engine Tests
# ============================================================

def _make_telemetry(building_id, room_id, n_records=48, energy_per_record=0.5,
                    power_kw=1.0, start=None, dt_seconds=300,
                    manipulated_fraction=0.0):
    """Generate synthetic telemetry for testing."""
    if start is None:
        start = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)  # Monday

    records = []
    for i in range(n_records):
        ts = start + timedelta(seconds=i * dt_seconds)
        is_manip = (i / n_records) < manipulated_fraction
        records.append({
            "timestamp": ts,
            "building_id": building_id,
            "room_id": room_id,
            "campus_id": "test_campus",
            "floor_id": "floor_1",
            "location_id": f"test.{building_id}.floor_1.{room_id}",
            "energy_interval_kwh": energy_per_record,
            "reported_power_kw": power_kw,
            "hvac_power_kw": power_kw * 0.4,
            "occupancy": 10 + i % 5,
            "reported_co2_ppm": 400 + i,
            "reported_temperature_c": 22.0 + (i % 3) * 0.5,
            "is_manipulated": is_manip,
            "attack_id": "atk_1" if is_manip else None,
            "attack_type": "OFFSET" if is_manip else None,
        })
    return pd.DataFrame(records)


class TestReportFiltering:
    """Verify that report filtering actually changes the underlying data."""

    def test_different_buildings_produce_different_energy(self):
        """Building A ≠ Building B when source telemetry differs."""
        from dashboard.reporting.engine import generate_report
        df_a = _make_telemetry("bldg_a", "R101", n_records=48, energy_per_record=1.0)
        df_b = _make_telemetry("bldg_b", "R201", n_records=48, energy_per_record=0.3)
        df = pd.concat([df_a, df_b], ignore_index=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report_a = generate_report(df, "bldg_a", "Building A", "Daily")
        report_b = generate_report(df, "bldg_b", "Building B", "Daily")

        assert report_a.has_data and report_b.has_data
        assert report_a.total_energy_kwh != report_b.total_energy_kwh
        assert report_a.total_energy_kwh == pytest.approx(48.0)
        assert report_b.total_energy_kwh == pytest.approx(14.4)

    def test_day_vs_week_produces_different_aggregation_rows(self):
        """Daily ≠ Weekly aggregation for the same data."""
        from dashboard.reporting.engine import generate_report
        # 7 days of data (7 * 288 = 2016 5-min records)
        df = _make_telemetry("bldg_a", "R101", n_records=2016, energy_per_record=0.1)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report_daily = generate_report(df, "bldg_a", "A", "Daily")
        report_weekly = generate_report(df, "bldg_a", "A", "Weekly")

        assert report_daily.aggregated_df is not None
        assert report_weekly.aggregated_df is not None
        # Daily should have 7 rows, Weekly should have 1
        assert len(report_daily.aggregated_df) == 7
        assert len(report_weekly.aggregated_df) == 1

    def test_time_range_filtering_changes_records(self):
        """Vacation/custom date range actually restricts the data."""
        from dashboard.reporting.engine import generate_report
        start = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)
        df = _make_telemetry("bldg_a", "R101", n_records=2016, energy_per_record=0.1, start=start)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report_full = generate_report(df, "bldg_a", "A", "Daily")
        report_partial = generate_report(
            df, "bldg_a", "A", "Daily",
            start_dt=start, end_dt=start + timedelta(days=2)
        )

        assert report_full.record_count > report_partial.record_count
        assert report_full.total_energy_kwh > report_partial.total_energy_kwh

    def test_no_telemetry_building_returns_empty(self):
        """A building with no data returns has_data=False."""
        from dashboard.reporting.engine import generate_report
        df = _make_telemetry("bldg_a", "R101", n_records=48)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report = generate_report(df, "nonexistent_building", "Ghost", "Daily")
        assert not report.has_data
        assert report.total_energy_kwh == 0.0
        assert report.record_count == 0

    def test_fdi_events_counted(self):
        """FDI events are accurately counted."""
        from dashboard.reporting.engine import generate_report
        df = _make_telemetry("bldg_a", "R101", n_records=100, manipulated_fraction=0.2)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report = generate_report(df, "bldg_a", "A", "Daily")
        assert report.fdi_event_count == 20  # 20% of 100

    def test_security_no_attacks(self):
        """No attacks produces zero FDI count."""
        from dashboard.reporting.engine import generate_report
        df = _make_telemetry("bldg_a", "R101", n_records=48, manipulated_fraction=0.0)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report = generate_report(df, "bldg_a", "A", "Daily")
        assert report.fdi_event_count == 0

    def test_hourly_aggregation(self):
        """Hourly aggregation produces correct number of groups."""
        from dashboard.reporting.engine import generate_report
        # 24 hours = 288 records at 5-min intervals
        df = _make_telemetry("bldg_a", "R101", n_records=288)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report = generate_report(df, "bldg_a", "A", "Hourly")
        assert report.aggregated_df is not None
        assert len(report.aggregated_df) == 24

    def test_monthly_aggregation(self):
        """Monthly aggregation groups by calendar month."""
        from dashboard.reporting.engine import generate_report
        # Span two months
        start = datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc)
        df = _make_telemetry("bldg_a", "R101", n_records=10000,
                            start=start, dt_seconds=300)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        report = generate_report(df, "bldg_a", "A", "Monthly")
        assert report.aggregated_df is not None
        assert len(report.aggregated_df) >= 2  # At least Jan + Feb
