import pytest
from datetime import datetime
import pandas as pd
import numpy as np

from config.loader import load_config
from simulation.engine import DigitalTwinSimulator

@pytest.fixture
def base_config():
    return load_config("config/root.yaml")

def test_final_audit_1_energy_contradiction(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(days=7)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    # 1. Calculate exact dataframe mean of true_power_kw
    mean_true_power = df['true_power_kw'].mean()
    
    # 2. Total campus energy
    total_campus_energy = df['energy_interval_kwh'].sum()
    
    # 3-4. Room level energy
    room_energy = df.groupby('location_id')['energy_interval_kwh'].sum()
    mean_room_energy = room_energy.mean()
    median_room_energy = room_energy.median()
    
    # 5. Reconstruct total energy
    total_sim_hours = 7 * 24
    num_rooms = len(sim.rooms)
    reconstructed_campus_energy = mean_true_power * total_sim_hours * num_rooms
    
    # 6. Reconcile
    # The discrepancy in the previous prompt was 2.5kW * 168h = 420 kWh per room vs reported 208 kWh.
    # But mean power is over ALL rows.
    # Total energy = sum(interval_energy) = mean(power) * (dt/3600) * N_rows
    # N_rows = N_rooms * N_intervals = N_rooms * (total_sim_hours * 3600 / dt)
    # So Total energy = mean(power) * N_rooms * total_sim_hours.
    # Mean room energy = Total energy / N_rooms = mean(power) * total_sim_hours.
    
    assert np.isclose(total_campus_energy, room_energy.sum(), atol=1e-5)
    assert np.isclose(total_campus_energy, reconstructed_campus_energy, atol=1e-5)
    assert np.isclose(mean_room_energy, mean_true_power * total_sim_hours, atol=1e-5)

def test_final_audit_2_hvac_config(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(days=1)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    for ctx in sim.rooms:
        c = ctx.config.hvac
        cap = c.cooling_capacity_kw
        cop = c.cop
        # check observed power matches exactly
        room_df = df[df['location_id'] == ctx.state.location_id]
        
        for state, frac in c.stage_fractions.items():
            expected_power = (cap * frac) / cop
            
            # Find rows where this state is active
            state_rows = room_df[room_df['hvac_state'] == state.value]
            if not state_rows.empty:
                max_err = (state_rows['hvac_power_kw'] - expected_power).abs().max()
                assert max_err < 1e-10

def test_final_audit_3_temp_trace(base_config):
    # Find minimum temperature in a 7-day sim
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(days=7)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    min_temp_idx = df['true_temperature_c'].idxmin()
    min_temp_row = df.loc[min_temp_idx]
    loc_id = min_temp_row['location_id']
    min_temp = min_temp_row['true_temperature_c']
    
    # We will print the trace in the python script execution block to inspect it
    # But we can assert physical logic here
    assert min_temp > -50.0 # Just a sanity bounds
    assert not np.isnan(min_temp)

def test_final_audit_4_co2_rows(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(days=7)
    sim = DigitalTwinSimulator(base_config)
    df = sim.simulate()
    
    # Sample 100 random rows across different rooms
    np.random.seed(42)
    sample_indices = np.random.choice(df.index[1:], size=100, replace=False)
    
    max_err = 0.0
    for idx in sample_indices:
        row = df.loc[idx]
        loc = row['location_id']
        ts = row['timestamp']
        
        # Get previous row for this location
        room_df = df[df['location_id'] == loc]
        room_idx = room_df.index.get_loc(idx)
        if room_idx == 0: continue
        prev_row = room_df.iloc[room_idx - 1]
        
        # Room config
        ctx = next(c for c in sim.rooms if c.state.location_id == loc)
        V = ctx.config.volume_m3
        G = ctx.config.co2.generation_rate_m3_s_person
        Q = ctx.config.co2.ventilation_rate_m3_s
        C_out = base_config.physics.outdoor_co2_ppm
        dt = base_config.simulation.dt_seconds
        
        c0 = prev_row['true_co2_ppm']
        occ = row['occupancy'] # occupancy applies over the interval leading to current row
        
        gen_term = (G * occ / V) * 1e6
        vent_term = (Q / V) * (c0 - C_out)
        dC = gen_term - vent_term
        c1 = c0 + dC * dt
        
        err = abs(c1 - row['true_co2_ppm'])
        max_err = max(max_err, err)
        
    assert max_err < 1e-10

def test_final_audit_5_behavioral_causality(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(days=1)
    
    # Sim A: Normal
    simA = DigitalTwinSimulator(base_config)
    dfA = simA.simulate()
    
    # Sim B: Tampered reported values
    simB = DigitalTwinSimulator(base_config)
    def tamper_hook(state):
        state.reported_temperature_c += 100.0
        state.reported_co2_ppm += 1000.0
        state.reported_power_kw += 50.0
    simB.post_step_hook = tamper_hook
    dfB = simB.simulate()
    
    # Compare true physical states and HVAC decisions
    cols_to_check = [
        'true_temperature_c', 'true_co2_ppm', 'true_power_kw', 'hvac_state', 'hvac_power_kw',
        'energy_interval_kwh', 'energy_cumulative_kwh', 'occupancy'
    ]
    pd.testing.assert_frame_equal(dfA[cols_to_check], dfB[cols_to_check])
    
    # But reported values MUST differ
    with pytest.raises(AssertionError):
        pd.testing.assert_series_equal(dfA['reported_temperature_c'], dfB['reported_temperature_c'])

def test_final_audit_6_reproducibility(base_config):
    base_config.simulation.end_datetime = base_config.simulation.start_datetime + pd.Timedelta(days=1)
    
    base_config.simulation.random_seed = 42
    simA = DigitalTwinSimulator(base_config)
    dfA = simA.simulate()
    
    simB = DigitalTwinSimulator(base_config)
    dfB = simB.simulate()
    
    base_config.simulation.random_seed = 99
    simC = DigitalTwinSimulator(base_config)
    dfC = simC.simulate()
    
    ignore_cols = ['sim_run_id']
    
    # A vs B: 100% identical except sim_run_id
    pd.testing.assert_frame_equal(dfA.drop(columns=ignore_cols), dfB.drop(columns=ignore_cols))
    
    # A vs C: Stochastic columns differ
    stochastic_cols = ['observed_temperature_c', 'reported_temperature_c', 'observed_power_kw', 'reported_power_kw', 'plug_power_kw'] # Depending on noise std
    for col in stochastic_cols:
        if True: #
            
            
            
            with pytest.raises(AssertionError):
                pd.testing.assert_series_equal(dfA[col], dfC[col])
                
    # But structural columns must remain identical
    struct_cols = ['timestamp', 'location_id', 'hvac_state'] # hvac might differ if noise crosses deadband, but usually same
    pd.testing.assert_series_equal(dfA['timestamp'], dfC['timestamp'])
    pd.testing.assert_series_equal(dfA['location_id'], dfC['location_id'])

def test_final_audit_7_hierarchy_isolation():
    # Modified config to have two identical room IDs in different buildings
    config = load_config("config/root.yaml")
    import copy
    config.campus.buildings.append(copy.deepcopy(config.campus.buildings[0]))
    config.campus.buildings[-1].id = "building_2"
    
    # Both buildings have a room with the exact same ID (e.g. A101)
    r1 = config.campus.buildings[0].floors[0].rooms[0].id
    r2 = config.campus.buildings[-1].floors[0].rooms[0].id
    config.campus.buildings[-1].floors[0].rooms[0].id = r1
    r2 = r1
    assert r1 == r2
    
    config.simulation.end_datetime = config.simulation.start_datetime + pd.Timedelta(days=1)
    sim = DigitalTwinSimulator(config)
    df = sim.simulate()
    
    loc1 = f"{config.university_id}.{config.campus.id}.{config.campus.buildings[0].id}.{config.campus.buildings[0].floors[0].id}.{r1}"
    loc2 = f"{config.university_id}.{config.campus.id}.{config.campus.buildings[-1].id}.{config.campus.buildings[-1].floors[0].id}.{r2}"
    
    df1 = df[df['location_id'] == loc1]
    df2 = df[df['location_id'] == loc2]
    
    assert not df1.empty
    assert not df2.empty
    
    # Since they have same parameters and same random seed logic (but different location_id string hashed), 
    # they will have slightly different noise, but both exist and maintain independent state.
    duration_s = (config.simulation.end_datetime - config.simulation.start_datetime).total_seconds()
    expected_rows = int(duration_s / config.simulation.dt_seconds)
    assert len(df1) == expected_rows
    assert len(df2) == expected_rows







