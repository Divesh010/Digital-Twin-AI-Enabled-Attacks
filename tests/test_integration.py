import pytest
from datetime import datetime, timedelta
import numpy as np

from models.occupancy import OccupancyModel
from models.environment import CO2Model, TemperatureModel
from models.hvac import HVACController
from models.power import LightingModel, PlugLoadModel, EnergyModel
from models.sensor import SensorModel
from config.models import HVACState

def test_a_occupancy_response():
    model = OccupancyModel(capacity=100, schedule_profile={"00:00": 0.0, "08:00": 1.0}, alpha=0.5, noise_std=0.0)
    dt = datetime.strptime("2026-09-01T08:00:00", "%Y-%m-%dT%H:%M:%S")
    o1 = model.step(dt)
    o2 = model.step(dt + timedelta(minutes=5))
    o3 = model.step(dt + timedelta(minutes=10))
    # Should gradually approach 100
    assert 0 < o1 < o2 < o3 <= 100

def test_b_co2_response():
    m1 = CO2Model(100, 5e-6, 0.1, 400.0)
    m2 = CO2Model(100, 5e-6, 0.1, 400.0)
    c1 = m1.step(300, 50, 400.0)
    c2 = m2.step(300, 10, 400.0)
    assert c1 > c2 # higher occupancy -> higher CO2
    
    m3 = CO2Model(100, 5e-6, 0.5, 1000.0)
    m4 = CO2Model(100, 5e-6, 0.1, 1000.0)
    c3 = m3.step(300, 0, 400.0)
    c4 = m4.step(300, 0, 400.0)
    assert c3 < c4 # higher ventilation -> drops faster to outdoor

def test_c_thermal_response():
    m1 = TemperatureModel(1e6, 0.02, 100, 24.0)
    m2 = TemperatureModel(1e6, 0.02, 100, 24.0)
    t1 = m1.step(300, 50, 0, 0, 0, 24.0)
    t2 = m2.step(300, 0, 0, 0, 0, 24.0)
    assert t1 > t2 # higher occupancy -> higher temp
    
    t3 = m1.step(300, 0, 0, 0, -5000, 24.0)
    assert t3 < t1 # HVAC cooling -> drops temp

def test_d_energy_response():
    energy = EnergyModel()
    p_tot, e_int, e_cum = energy.step(300, 0.5, 1.2, 0.5, 0.0)
    assert p_tot == 2.2 # base + light + plug + hvac (0)
    
    p_tot_hvac, _, _ = energy.step(300, 0.5, 1.2, 0.5, 2.0)
    assert p_tot_hvac == 4.2 # hvac added
    assert p_tot_hvac > p_tot

def test_e_closed_loop_hvac():
    temp = TemperatureModel(1e6, 0.02, 100, 24.0)
    sensor = SensorModel(bias=0.1, noise_std=0.0, drift_rate=0.0, resolution=0.0)
    hvac = HVACController(10.0, 3.0, 24.0, 1.0, 1.0, 5.0, 5.0, {HVACState.OFF: 0.0, HVACState.LOW: 1.0, HVACState.MEDIUM: 1.0, HVACState.HIGH: 1.0})
    
    # temp is 24.0, sensor sees 24.1
    # step 1: external heat applied
    for _ in range(10):
        obs = sensor.step(300, temp.current_temp_c)
        state, p_kw, th_w = hvac.step(300, obs)
        t_true = temp.step(300, 10, 0, 0, th_w, 35.0)
    
    # Over 10 steps (50 mins) with 35C outdoor and 10 people, temp should rise, trigger HVAC, and stabilize
    assert temp.current_temp_c < 30.0
    assert hvac.current_state != HVACState.OFF

def test_f_24_hour_stability():
    occ_model = OccupancyModel(100, {"00:00": 0.0, "08:00": 1.0, "18:00": 0.0}, 0.2, 0.0)
    co2_model = CO2Model(200, 5e-6, 0.1, 400.0)
    temp_model = TemperatureModel(1e6, 0.02, 100, 24.0)
    hvac = HVACController(10.0, 3.0, 24.0, 1.0, 1.0, 5.0, 5.0, {HVACState.OFF: 0.0, HVACState.LOW: 0.5, HVACState.MEDIUM: 0.75, HVACState.HIGH: 1.0})
    light = LightingModel(1.5)
    plug = PlugLoadModel(0.05, 0.0)
    energy = EnergyModel()
    sensor = SensorModel(0.0, 0.0, 0.0, 0.1)
    
    dt = datetime.strptime("2026-09-01T00:00:00", "%Y-%m-%dT%H:%M:%S")
    
    for _ in range(288): # 24 hours at 5 mins
        o = occ_model.step(dt)
        assert 0 <= o <= 100
        
        c = co2_model.step(300, o, 400.0)
        assert c >= 0
        assert not np.isnan(c)
        
        t_obs = sensor.step(300, temp_model.current_temp_c)
        state, p_kw, th_w = hvac.step(300, t_obs)
        
        p_light = light.step(o)
        p_plug = plug.step(o)
        p_tot, e_int, e_cum = energy.step(300, 0.5, p_light, p_plug, p_kw)
        
        t = temp_model.step(300, o, p_light*1000, p_plug*1000, th_w, 30.0)
        assert not np.isnan(t)
        assert p_tot >= 0
        assert e_int >= 0
        
        dt += timedelta(minutes=5)
    
    assert energy.cumulative_energy_kwh > 0
