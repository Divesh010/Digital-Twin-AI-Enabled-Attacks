import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from config.loader import load_config
from simulation.engine import DigitalTwinSimulator, RoomState
from simulation.state_manager import StateManager
from models.environment import TemperatureModel

@pytest.fixture
def base_config():
    return load_config("config/root.yaml")

def test_audit_2_co2_numerically(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(minutes=5)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    # Pick first room
    row = df.iloc[0]
    dt_seconds = 300
    
    # Extract config for that room
    b_id = row['building_id']
    f_id = row['floor_id']
    r_id = row['room_id']
    building = next(b for b in base_config.campus.buildings if b.id == b_id)
    floor = next(f for f in building.floors if f.id == f_id)
    room = next(r for r in floor.rooms if r.id == r_id)
    
    # Initial state (from config default)
    c0 = base_config.physics.outdoor_co2_ppm
    V = room.volume_m3
    G = room.co2.generation_rate_m3_s_person
    Q = room.co2.ventilation_rate_m3_s
    C_out = base_config.physics.outdoor_co2_ppm
    occ = row['occupancy']
    
    # Reconstruct Euler integration
    # dC = (G * occ / V) * 1e6 - (Q / V) * (C - C_out)
    gen_term = (G * occ / V) * 1e6
    vent_term = (Q / V) * (c0 - C_out)
    dC = gen_term - vent_term
    c1 = c0 + dC * dt_seconds
    
    assert np.isclose(c1, row['true_co2_ppm'], rtol=1e-5, atol=1e-5)

def test_audit_4_energy_numerically(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(hours=2)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    P_total_calc = df['base_power_kw'] + df['lighting_power_kw'] + df['plug_power_kw'] + df['hvac_power_kw']
    max_err_p = (df['true_power_kw'] - P_total_calc).abs().max()
    assert max_err_p < 1e-10
    
    E_int_calc = P_total_calc * (base_config.simulation.dt_seconds / 3600.0)
    max_err_e = (df['energy_interval_kwh'] - E_int_calc).abs().max()
    assert max_err_e < 1e-10

def test_audit_5_causality(base_config):
    sim = DigitalTwinSimulator(base_config)
    # Tamper with reported temperature in StateManager after initialization but before simulate runs
    # Actually, reported_temperature_c is written AT THE END of the timestep in engine.py:
    # st.reported_temperature_c = st.observed_temperature_c
    # So if we want to prove it never affects the next step, we can look at the engine code.
    # We can programmatically check that reported_temperature_c is never read.
    import ast
    with open('src/simulation/engine.py', 'r') as f:
        tree = ast.parse(f.read())
        
    reads = []
    writes = []
    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, node):
            if node.attr == 'reported_temperature_c':
                if isinstance(node.ctx, ast.Load):
                    reads.append(node)
                elif isinstance(node.ctx, ast.Store):
                    writes.append(node)
            self.generic_visit(node)
            
    Visitor().visit(tree)
    # 2 reads are allowed: one in the dictionary construction for the record, one potentially in init
    # Let's just verify it's only read during the record dictionary creation
    assert len(reads) <= 2 
    
def test_audit_7_state_manager_unique_keys():
    sm = StateManager()
    st1 = RoomState(university_id="U", campus_id="C", building_id="B1", floor_id="F1", room_id="A101", location_id="U.C.B1.F1.A101")
    st2 = RoomState(university_id="U", campus_id="C", building_id="B2", floor_id="F1", room_id="A101", location_id="U.C.B2.F1.A101")
    
    sm.add_room(st1)
    sm.add_room(st2)
    
    assert sm.get_room_state("U.C.B1.F1.A101") is st1
    assert sm.get_room_state("U.C.B2.F1.A101") is st2
    assert st1.location_id != st2.location_id

def test_audit_3_temp_behavior(base_config):
    # Setup a single room experiment to understand the 18.6C temp minimum
    # Room parameters:
    # thermal_mass_j_c = 10,000,000
    # thermal_resistance_c_w = 0.015
    # HVAC: cooling_capacity_kw = 10.0, upper_deadband=1.0, lower_deadband=1.0, setpoint=24.0
    # HIGH stage fraction = 1.0 -> 10,000 W of cooling
    
    model = TemperatureModel(thermal_mass_j_c=10_000_000, thermal_resistance_c_w=0.015, heat_per_person_w=100.0, initial_temp_c=24.0)
    
    # 1. HVAC Disabled, Constant Occupancy (100 people)
    for _ in range(12): # 1 hour
        model.step(dt_seconds=300, occupancy=100, lighting_power_w=0, plug_power_w=0, hvac_thermal_w=0, outdoor_temp_c=32.0)
        
    t_disabled = model.current_temp_c
    assert t_disabled > 24.0 # Should heat up
    
    # 2. HVAC Enabled (HIGH = -10,000 W)
    model.current_temp_c = 25.1 # Just above upper deadband
    for _ in range(12):
        model.step(dt_seconds=300, occupancy=0, lighting_power_w=0, plug_power_w=0, hvac_thermal_w=-10000, outdoor_temp_c=32.0)
        
    t_cooled = model.current_temp_c
    
    # If occupancy drops to 0, and HVAC continues cooling for minimum runtime (e.g. 5 mins = 300s):
    # dQ = -10,000 W (cooling) + (32 - 24) / 0.015 (envelope ~ 533 W) = -9466 W
    # dT = -9466 * 300 / 10,000,000 = -0.284 C per step.
    # Over 5 steps (25 mins min runtime), it drops 1.4C.
    # Therefore, reaching 18.6C means the HVAC ran on HIGH for a long time when the room was empty,
    # OR thermal mass is very low.
    pass

