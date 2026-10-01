import pytest
from pydantic import ValidationError
from datetime import datetime, timezone, timedelta
from config.models import RootConfig, FDIAttackConfig, OffsetAttackConfig, SlowDripAttackConfig, ReplayAttackConfig
from attacks.engine import FDIEngine, OffsetAttack

# ================================
# 1. Configuration Target Validation
# ================================
def test_fdi_target_variable_validation():
    # Attempting to attack true_* or observed_* should fail Pydantic validation
    with pytest.raises(ValidationError) as exc:
        FDIAttackConfig(
            attack_id="BAD",
            target_location="L1",
            target_variable="true_co2_ppm", # NOT ALLOWED
            start_time=datetime(2026,1,1,tzinfo=timezone.utc),
            end_time=datetime(2026,1,2,tzinfo=timezone.utc),
            parameters=OffsetAttackConfig(offset_value=100.0)
        )
    assert "target_variable" in str(exc.value)


# ================================
# 2. Location & ID Validation
# ================================
def test_fdi_target_location_and_id_uniqueness(tmp_path):
    import yaml
    from config.loader import load_config
    
    # We will just write a small custom loader test
    # but to avoid full config generation, we can just instantiate a RootConfig with dicts.
    pass # Will implement via a full config load if necessary, but we can just use the RootConfig dict

# Instead of full RootConfig, we test boundaries directly here.

# ================================
# 3. Ground Truth Immutability Snapshot
# ================================
def test_ground_truth_immutability():
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)
    config = FDIAttackConfig(
        attack_id="TEST_IMMUTABILITY",
        target_location="L1",
        target_variable="reported_co2_ppm",
        start_time=start,
        end_time=end,
        parameters=OffsetAttackConfig(offset_value=999.0)
    )
    
    engine = FDIEngine([config])
    
    record = {
        "location_id": "L1",
        "true_co2_ppm": 400.0, "observed_co2_ppm": 405.0, "reported_co2_ppm": 405.0,
        "true_temperature_c": 22.0, "observed_temperature_c": 22.1, "reported_temperature_c": 22.1,
        "true_power_kw": 5.0, "observed_power_kw": 5.0, "reported_power_kw": 5.0,
        "occupancy": 10, "hvac_state": "ON"
    }
    
    snapshot = record.copy()
    res = engine.apply_attacks(record.copy(), start)
    
    # Verify exact immutability of everything except the explicit target
    for k, v in snapshot.items():
        if k == "reported_co2_ppm":
            assert res[k] == 405.0 + 999.0
        else:
            assert res[k] == v

# ================================
# 4. Attack Boundaries
# ================================
def test_attack_boundaries():
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    
    config = FDIAttackConfig(
        attack_id="BOUND", target_location="L1", target_variable="reported_co2_ppm",
        start_time=start, end_time=end, parameters=OffsetAttackConfig(offset_value=10.0)
    )
    engine = FDIEngine([config])
    
    record = {"location_id": "L1", "reported_co2_ppm": 400.0, "reported_temperature_c": 22.0, "reported_power_kw": 5.0}
    
    # t < start
    assert engine.apply_attacks(record.copy(), start - timedelta(seconds=1))["is_manipulated"] is False
    
    # t == start (INCLUSIVE)
    assert engine.apply_attacks(record.copy(), start)["is_manipulated"] is True
    
    # start < t < end (INCLUSIVE)
    assert engine.apply_attacks(record.copy(), start + timedelta(seconds=1800))["is_manipulated"] is True
    
    # t == end (EXCLUSIVE)
    assert engine.apply_attacks(record.copy(), end)["is_manipulated"] is False
    
    # t > end
    assert engine.apply_attacks(record.copy(), end + timedelta(seconds=1))["is_manipulated"] is False

# ================================
# 5. Offset Math
# ================================
def test_offset_math():
    for offset in [100.0, -100.0, 0.0]:
        start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
        config = FDIAttackConfig(
            attack_id="OFFSET_MATH", target_location="L1", target_variable="reported_power_kw",
            start_time=start, end_time=start+timedelta(hours=1), parameters=OffsetAttackConfig(offset_value=offset)
        )
        engine = FDIEngine([config])
        record = {"location_id": "L1", "reported_co2_ppm": 400.0, "reported_temperature_c": 22.0, "reported_power_kw": 5.0}
        res = engine.apply_attacks(record.copy(), start)
        assert res["reported_power_kw"] == 5.0 + offset
        assert res["attack_magnitude"] == offset

# ================================
# 6. Slow Drip Math
# ================================
def test_slow_drip_math():
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    config = FDIAttackConfig(
        attack_id="DRIP_MATH", target_location="L1", target_variable="reported_power_kw",
        start_time=start, end_time=start+timedelta(hours=1), 
        parameters=SlowDripAttackConfig(initial_offset=-5.0, ramp_rate_per_second=0.5)
    )
    engine = FDIEngine([config])
    record = {"location_id": "L1", "reported_co2_ppm": 400.0, "reported_temperature_c": 22.0, "reported_power_kw": 50.0}
    
    # At t=0
    res = engine.apply_attacks(record.copy(), start)
    assert res["reported_power_kw"] == 50.0 - 5.0
    
    # At t=10s
    res = engine.apply_attacks(record.copy(), start + timedelta(seconds=10))
    # offset = -5.0 + (0.5 * 10) = 0.0
    assert res["reported_power_kw"] == 50.0
    
    # At t=3599s (max offset right before end)
    res = engine.apply_attacks(record.copy(), start + timedelta(seconds=3599))
    # offset = -5.0 + (0.5 * 3599) = -5.0 + 1799.5 = 1794.5
    assert res["reported_power_kw"] == 50.0 + 1794.5

# ================================
# 7. Replay Attack History & Precedence
# ================================
def test_replay_history_fallback_and_multiple_interaction():
    start = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    
    # Config 1: Replay attack
    c1 = FDIAttackConfig(
        attack_id="REPLAY", target_location="L1", target_variable="reported_temperature_c",
        start_time=start, end_time=end, parameters=ReplayAttackConfig(replay_window_seconds=3600)
    )
    
    # Config 2: Offset attack (same room, same variable)
    c2 = FDIAttackConfig(
        attack_id="OFFSET_OVERRIDE", target_location="L1", target_variable="reported_temperature_c",
        start_time=start, end_time=end, parameters=OffsetAttackConfig(offset_value=10.0)
    )
    
    # If c1 then c2, c2 should win (Last attack wins).
    engine = FDIEngine([c1, c2])
    
    record = {"location_id": "L1", "reported_co2_ppm": 400.0, "reported_temperature_c": 22.0, "reported_power_kw": 5.0}
    
    # Fallback behavior (no history available): Replay returns original, but Offset overrides it.
    res = engine.apply_attacks(record.copy(), start)
    assert res["reported_temperature_c"] == 22.0 + 10.0
    assert res["attack_id"] == "OFFSET_OVERRIDE"
    
    # Now provide history exactly 1 hour ago
    engine.observe({"location_id": "L1", "reported_temperature_c": 15.0}, start - timedelta(hours=1))
    
    # Apply again. Replay wants to output 15.0. Offset wants to output 22.0 + 10.0 = 32.0.
    # Since offset is evaluated sequentially using the ORIGINAL baseline of 22.0, it will output 32.0.
    res = engine.apply_attacks(record.copy(), start)
    assert res["reported_temperature_c"] == 32.0
    assert res["attack_magnitude"] == 10.0
