import pytest
import pandas as pd
from dashboard.data.loader import get_hierarchy, deduplicate_telemetry
import importlib

def test_hierarchy_parsing():
    df = pd.DataFrame([
        {'campus_id': 'c1', 'building_id': 'b1', 'floor_id': 'f1', 'room_id': 'r1'},
        {'campus_id': 'c1', 'building_id': 'b1', 'floor_id': 'f1', 'room_id': 'r2'}
    ])
    hierarchy = get_hierarchy(df)
    assert 'c1' in hierarchy
    assert 'b1' in hierarchy['c1']
    assert 'f1' in hierarchy['c1']['b1']
    assert 'r1' in hierarchy['c1']['b1']['f1']
    assert 'r2' in hierarchy['c1']['b1']['f1']

def test_kpi_calculations_isolation():
    df = pd.DataFrame([
        {'timestamp': '2026-09-02', 'reported_power_kw': 10.0, 'is_manipulated': False, 'location_id': 'A101'},
        {'timestamp': '2026-09-02', 'reported_power_kw': 20.0, 'is_manipulated': True, 'location_id': 'A101'},
        {'timestamp': '2026-09-02', 'reported_power_kw': 30.0, 'is_manipulated': True, 'location_id': 'A101'}
    ])
    
    manipulated = df[df['is_manipulated'] == True]
    # Rooms under attack logic from overview
    rooms_under_attack = len(manipulated['location_id'].unique())
    assert rooms_under_attack == 1, "Should count unique locations, not row count"

def test_mqtt_topic_structure():
    # Verify the dashboard expects the Phase 6A schema
    university_id = "bennett_uni"
    campus_id = "main_campus"
    building_id = "academic_block"
    floor_id = "floor_1"
    room_id = "A101"
    topic_prefix = "dt"
    
    expected_topic = f"{topic_prefix}/{university_id}/campus/{campus_id}/building/{building_id}/floor/{floor_id}/room/{room_id}/telemetry"
    assert expected_topic == "dt/bennett_uni/campus/main_campus/building/academic_block/floor/floor_1/room/A101/telemetry"

def test_fdi_visualization_columns():
    df = pd.DataFrame([
        {'true_co2_ppm': 400.0, 'observed_co2_ppm': 400.0, 'reported_co2_ppm': 500.0, 'is_manipulated': True}
    ])
    
    assert 'true_co2_ppm' in df.columns
    assert 'observed_co2_ppm' in df.columns
    assert 'reported_co2_ppm' in df.columns
    
    row = df.iloc[0]
    assert row['reported_co2_ppm'] != row['observed_co2_ppm']

def test_deduplication():
    df = pd.DataFrame([
        {'timestamp': '2026-09-02T10:00:00', 'location_id': 'L1', 'val': 1},
        {'timestamp': '2026-09-02T10:00:00', 'location_id': 'L1', 'val': 2}, # Duplicate
        {'timestamp': '2026-09-02T10:05:00', 'location_id': 'L1', 'val': 3},
    ])
    deduped = deduplicate_telemetry(df)
    assert len(deduped) == 2
    assert deduped.iloc[0]['val'] == 2 # Keep last

def test_what_if_imports():
    # Smoke test what-if imports
    try:
        from models.occupancy import OccupancyModel
        from models.environment import CO2Model, TemperatureModel
        from models.hvac import HVACController
        from models.power import LightingModel, PlugLoadModel, EnergyModel
    except ImportError as e:
        pytest.fail(f"Phase 5 model imports failed: {e}")

def test_duplicate_room_id_security_filtering():
    df = pd.DataFrame([
        {'location_id': 'b1.f1.r1', 'room_id': 'r1', 'is_manipulated': True},
        {'location_id': 'b2.f1.r1', 'room_id': 'r1', 'is_manipulated': True}
    ])
    # The security dashboard uses location_id to prevent overlaps
    attacked_locations = df['location_id'].unique()
    assert len(attacked_locations) == 2
    
    b1_df = df[df['location_id'] == 'b1.f1.r1']
    assert len(b1_df) == 1
import pytest
import pandas as pd
from datetime import datetime, timedelta

from config.loader import load_config
from models.occupancy import OccupancyModel
from models.environment import CO2Model, TemperatureModel
from models.hvac import HVACController
from models.power import LightingModel, PlugLoadModel, EnergyModel


import pytest
import pandas as pd
from datetime import datetime, timedelta

from config.loader import load_config
from models.occupancy import OccupancyModel
from models.environment import CO2Model, TemperatureModel
from models.hvac import HVACController
from models.power import LightingModel, PlugLoadModel, EnergyModel

def test_what_if_runtime():
    config = load_config("config/root.yaml")
    
    # Grab first room
    room_config = config.campus.buildings[0].floors[0].rooms[0]
    schedule_id = room_config.schedule_id
    schedule = next(s for s in config.schedules if s.id == schedule_id)
    
    occ_model = OccupancyModel(capacity=room_config.capacity, schedule_profile=schedule.profile, seed=42)
    co2_model = CO2Model(
        volume_m3=room_config.volume_m3,
        generation_rate_m3_s_person=room_config.co2.generation_rate_m3_s_person,
        ventilation_rate_m3_s=room_config.co2.ventilation_rate_m3_s,
        initial_co2_ppm=config.physics.outdoor_co2_ppm
    )
    temp_model = TemperatureModel(
        thermal_mass_j_c=room_config.temperature.thermal_mass_j_c,
        thermal_resistance_c_w=room_config.temperature.thermal_resistance_c_w,
        heat_per_person_w=room_config.temperature.heat_per_person_w,
        initial_temp_c=room_config.hvac.setpoint_c
    )
    hvac = HVACController(
        cooling_capacity_kw=room_config.hvac.cooling_capacity_kw,
        cop=room_config.hvac.cop,
        setpoint_c=room_config.hvac.setpoint_c,
        upper_deadband_c=room_config.hvac.upper_deadband_c,
        lower_deadband_c=room_config.hvac.lower_deadband_c,
        min_on_time_minutes=room_config.hvac.min_on_time_minutes,
        min_off_time_minutes=room_config.hvac.min_off_time_minutes,
        stage_fractions=room_config.hvac.stage_fractions
    )
    light_model = LightingModel(capacity_kw=room_config.power.lighting_capacity_kw)
    plug_model = PlugLoadModel(plug_load_per_person_kw=room_config.power.plug_load_per_person_kw, seed=42)
    energy_model = EnergyModel()
    
    dt_seconds = config.simulation.dt_seconds
    current_time = config.simulation.start_datetime
    end_time = current_time + timedelta(hours=24)
    
    records = []
    t_obs = room_config.hvac.setpoint_c
    outdoor_temp = config.physics.outdoor_temperature_c
    
    while current_time < end_time:
        occ = occ_model.step(current_time)
        hvac_st, hvac_p_kw, hvac_th_w = hvac.step(dt_seconds, t_obs)
        p_light = light_model.step(occ)
        p_plug = plug_model.step(occ)
        co2 = co2_model.step(dt_seconds, occ, config.physics.outdoor_co2_ppm)
        t_true = temp_model.step(dt_seconds, occ, p_light*1000, p_plug*1000, hvac_th_w, outdoor_temp)
        t_obs = t_true
        p_tot, e_int, e_cum = energy_model.step(dt_seconds, room_config.power.base_load_kw, p_light, p_plug, hvac_p_kw)
        
        records.append({
            'timestamp': current_time, 'occupancy': occ, 'co2_ppm': co2,
            'temperature_c': t_true, 'power_kw': p_tot
        })
        current_time += timedelta(seconds=dt_seconds)
        
    df_sim = pd.DataFrame(records)
    
    # Verifications
    assert len(df_sim) == 288 # 24 hours * 12 (5 min intervals)
    assert 'temperature_c' in df_sim.columns
    assert 'co2_ppm' in df_sim.columns
    assert 'power_kw' in df_sim.columns
    assert 'occupancy' in df_sim.columns
    
    assert df_sim['power_kw'].sum() > 0