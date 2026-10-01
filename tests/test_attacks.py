import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from config.models import FDIAttackConfig, OffsetAttackConfig, SlowDripAttackConfig, ReplayAttackConfig
from attacks.engine import FDIEngine

def test_offset_attack():
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)
    
    config = FDIAttackConfig(
        attack_id="TEST_OFFSET",
        target_location="L1",
        target_variable="reported_co2_ppm",
        start_time=start,
        end_time=end,
        parameters=OffsetAttackConfig(offset_value=-100.0)
    )
    
    engine = FDIEngine([config])
    
    # 1. Before attack
    t_before = start - timedelta(seconds=1)
    record = {"location_id": "L1", "reported_co2_ppm": 500.0}
    res = engine.apply_attacks(record.copy(), t_before)
    assert res["is_manipulated"] is False
    assert res["reported_co2_ppm"] == 500.0
    
    # 2. During attack
    t_during = start + timedelta(hours=1)
    res = engine.apply_attacks(record.copy(), t_during)
    assert res["is_manipulated"] is True
    assert res["attack_id"] == "TEST_OFFSET"
    assert res["reported_co2_ppm"] == 400.0
    assert res["attack_magnitude"] == -100.0
    
    # 3. After attack
    t_after = end
    res = engine.apply_attacks(record.copy(), t_after)
    assert res["is_manipulated"] is False
    assert res["reported_co2_ppm"] == 500.0
    
    # 4. Different room
    record_other = {"location_id": "L2", "reported_co2_ppm": 500.0}
    res = engine.apply_attacks(record_other.copy(), t_during)
    assert res["is_manipulated"] is False
    assert res["reported_co2_ppm"] == 500.0


def test_slow_drip_attack():
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1) # 3600 seconds
    
    config = FDIAttackConfig(
        attack_id="TEST_DRIP",
        target_location="L1",
        target_variable="reported_power_kw",
        start_time=start,
        end_time=end,
        parameters=SlowDripAttackConfig(initial_offset=1.0, ramp_rate_per_second=0.01)
    )
    
    engine = FDIEngine([config])
    
    # Start: offset = 1.0 + (0 * 0.01) = 1.0
    record = {"location_id": "L1", "reported_power_kw": 5.0, "reported_co2_ppm": 400.0, "reported_temperature_c": 22.0}
    res = engine.apply_attacks(record.copy(), start)
    assert res["reported_power_kw"] == 6.0
    
    # Halfway (1800s): offset = 1.0 + (1800 * 0.01) = 1.0 + 18.0 = 19.0
    t_half = start + timedelta(seconds=1800)
    res = engine.apply_attacks(record.copy(), t_half)
    assert res["reported_power_kw"] == 24.0
    assert res["attack_magnitude"] == 19.0


def test_replay_attack():
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    
    config = FDIAttackConfig(
        attack_id="TEST_REPLAY",
        target_location="L1",
        target_variable="reported_temperature_c",
        start_time=start,
        end_time=end,
        parameters=ReplayAttackConfig(replay_window_seconds=3600) # Replay 1 hour ago
    )
    
    engine = FDIEngine([config])
    
    t_history = start - timedelta(hours=1)
    
    # Feed history
    engine.observe({"location_id": "L1", "reported_temperature_c": 22.5}, t_history)
    engine.observe({"location_id": "L2", "reported_temperature_c": 99.0}, t_history)
    
    # Apply attack
    record = {"location_id": "L1", "reported_temperature_c": 26.0, "reported_power_kw": 5.0, "reported_co2_ppm": 400.0}
    res = engine.apply_attacks(record.copy(), start)
    
    assert res["is_manipulated"] is True
    assert res["reported_temperature_c"] == 22.5 # Extracted from exactly 1 hour ago
    assert res["attack_magnitude"] == -3.5


def test_attack_metadata_baseline_preservation():
    # Verify that true_*, observed_* remain completely untouched
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)
    
    config = FDIAttackConfig(
        attack_id="TEST_METADATA",
        target_location="L1",
        target_variable="reported_co2_ppm",
        start_time=start,
        end_time=end,
        parameters=OffsetAttackConfig(offset_value=100.0)
    )
    
    engine = FDIEngine([config])
    record = {
        "location_id": "L1", 
        "true_co2_ppm": 400.0,
        "observed_co2_ppm": 405.0,
        "reported_co2_ppm": 405.0
    }
    
    res = engine.apply_attacks(record.copy(), start)
    
    assert res["true_co2_ppm"] == 400.0
    assert res["observed_co2_ppm"] == 405.0
    assert res["reported_co2_ppm"] == 505.0
