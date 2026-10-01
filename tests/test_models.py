import pytest
from datetime import datetime
import numpy as np

from models.occupancy import OccupancyModel
from models.environment import CO2Model, TemperatureModel
from models.hvac import HVACController
from models.power import LightingModel, PlugLoadModel, EnergyModel
from models.sensor import SensorModel
from config.models import HVACState

def test_occupancy_model():
    profile = {"00:00": 0.0, "08:00": 0.5, "12:00": 1.0}
    model = OccupancyModel(capacity=100, schedule_profile=profile, alpha=0.5, noise_std=0.0)
    
    dt = datetime.strptime("2026-09-01T07:00:00", "%Y-%m-%dT%H:%M:%S")
    occ = model.step(dt)
    assert occ == 0
    
    dt = datetime.strptime("2026-09-01T09:00:00", "%Y-%m-%dT%H:%M:%S")
    occ = model.step(dt)
    assert occ == 25
    
    dt = datetime.strptime("2026-09-01T09:05:00", "%Y-%m-%dT%H:%M:%S")
    occ = model.step(dt)
    assert occ == 38

def test_co2_model():
    model = CO2Model(volume_m3=100, generation_rate_m3_s_person=5e-6, ventilation_rate_m3_s=0.1, initial_co2_ppm=500.0)
    for _ in range(12):
        c = model.step(dt_seconds=300, occupancy=0, outdoor_co2_ppm=400.0)
    assert 400.0 <= c < 410.0
    
    c = model.step(dt_seconds=300, occupancy=50, outdoor_co2_ppm=400.0)
    assert c > 400.0

def test_temperature_model():
    model = TemperatureModel(thermal_mass_j_c=1e6, thermal_resistance_c_w=0.02, heat_per_person_w=100, initial_temp_c=24.0)
    t1 = model.step(dt_seconds=300, occupancy=0, lighting_power_w=0, plug_power_w=0, hvac_thermal_w=0, outdoor_temp_c=20.0)
    assert t1 < 24.0

    t2 = model.step(dt_seconds=300, occupancy=0, lighting_power_w=0, plug_power_w=0, hvac_thermal_w=-5000, outdoor_temp_c=20.0)
    assert t2 < t1

def test_hvac_controller():
    ctrl = HVACController(cooling_capacity_kw=10.0, cop=3.0, setpoint_c=24.0, upper_deadband_c=1.0, lower_deadband_c=1.0, 
                          min_on_time_minutes=5.0, min_off_time_minutes=5.0, stage_fractions={HVACState.OFF: 0.0, HVACState.LOW: 0.5, HVACState.MEDIUM: 0.75, HVACState.HIGH: 1.0})
    
    state, p_kw, th_w = ctrl.step(300, 24.0)
    assert state == HVACState.OFF
    assert p_kw == 0.0
    
    state, p_kw, th_w = ctrl.step(300, 26.0)
    assert state == HVACState.LOW
    assert th_w == -5000.0
    
    state, p_kw, th_w = ctrl.step(300, 26.0)
    assert state == HVACState.MEDIUM
    
    state, p_kw, th_w = ctrl.step(300, 22.0)
    assert state == HVACState.LOW

def test_power_models():
    light = LightingModel(capacity_kw=1.5)
    assert light.step(0) == 0.0
    assert light.step(10) == 1.5
    
    plug = PlugLoadModel(plug_load_per_person_kw=0.1, noise_std=0.0)
    assert plug.step(0) == 0.0
    assert plug.step(10) == 1.0

def test_energy_model():
    energy = EnergyModel()
    p_tot, e_int, e_cum = energy.step(3600, 0.5, 1.0, 0.5, 2.0)
    assert p_tot == 4.0
    assert e_int == 4.0
    assert e_cum == 4.0

def test_sensor_model():
    sensor = SensorModel(bias=0.0, noise_std=0.0, drift_rate=0.01, resolution=0.0)
    obs_t0 = sensor.step(300, 24.0)
    assert abs(obs_t0 - 24.0) < 1e-6
    
    obs_t1 = sensor.step(300, 24.0)
    assert abs(obs_t1 - 27.0) < 1e-6
    
    obs_t2 = sensor.step(300, 24.0)
    assert abs(obs_t2 - 30.0) < 1e-6
