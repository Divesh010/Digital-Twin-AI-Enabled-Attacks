import pytest
from datetime import datetime
from pathlib import Path
import pandas as pd

from config.loader import load_config
from simulation.engine import DigitalTwinSimulator

@pytest.fixture
def base_config():
    root_path = Path("config/root.yaml")
    return load_config(str(root_path))

def test_1_and_2_record_counts(base_config):
    # Set to 1 hour
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(hours=1)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    # 1 hour at 5 min = 12 steps. 
    num_rooms = len(sim.rooms)
    assert len(df) == 12 * num_rooms
    assert len(df.groupby(['timestamp'])) == 12
    assert len(df.groupby(['room_id'])) == num_rooms

def test_3_canonical_fields(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(hours=1)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    expected_cols = [
        "timestamp", "university_id", "campus_id", "building_id", "floor_id", "room_id", "sensor_id",
        "occupancy", "occupancy_pct", "true_co2_ppm", "observed_co2_ppm", "reported_co2_ppm",
        "true_temperature_c", "observed_temperature_c", "reported_temperature_c", "humidity_pct",
        "hvac_state", "hvac_power_kw", "lighting_power_kw", "plug_power_kw", "base_power_kw",
        "true_power_kw", "observed_power_kw", "reported_power_kw", "energy_interval_kwh", "energy_cumulative_kwh",
        "outdoor_temperature_c", "outdoor_humidity_pct", "outdoor_co2_ppm", "data_source",
        "is_missing", "is_imputed", "is_sensor_fault", "is_outlier", "is_manipulated",
        "sim_run_id", "model_version", "config_version", "random_seed"
    ]
    for col in expected_cols:
        assert col in df.columns

def test_4_and_5_seeds(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(hours=1)
    
    base_config.simulation.random_seed = 42
    sim1 = DigitalTwinSimulator(base_config)
    df1 = sim1.simulate()
    
    sim2 = DigitalTwinSimulator(base_config)
    df2 = sim2.simulate()
    
    base_config.simulation.random_seed = 99
    sim3 = DigitalTwinSimulator(base_config)
    df3 = sim3.simulate()
    
    # Same seed -> identical, dropping sim_run_id as it varies
    pd.testing.assert_frame_equal(df1.drop(columns=['sim_run_id']), df2.drop(columns=['sim_run_id']))
    
    # Different seed -> stochastic differences (e.g. observed_temp_c)
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(df1.drop(columns=['sim_run_id']), df3.drop(columns=['sim_run_id']))

def test_6_to_12_stability_and_physics(base_config):
    # Run 24h
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(days=1)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    # 8. Energy consistency
    calc_p = df['base_power_kw'] + df['lighting_power_kw'] + df['plug_power_kw'] + df['hvac_power_kw']
    assert (abs(df['true_power_kw'] - calc_p) < 1e-5).all()
    
    calc_e = df['true_power_kw'] * (base_config.simulation.dt_seconds / 3600.0)
    assert (abs(df['energy_interval_kwh'] - calc_e) < 1e-5).all()
    
    # 9. Monotonic energy
    for r, g in df.groupby('room_id'):
        assert g['energy_cumulative_kwh'].is_monotonic_increasing
        
    # 10. Bounds
    assert (df['occupancy'] >= 0).all()
    assert (df['occupancy_pct'] <= 100.0).all()
    assert (df['true_co2_ppm'] >= 0).all()
    assert not df['true_temperature_c'].isna().any()
    
    # 11. Reported = observed
    assert (df['reported_temperature_c'] == df['observed_temperature_c']).all()
    
    # 12. FDI fields inactive
    assert not df['is_manipulated'].any()
    assert not df['is_missing'].any()
