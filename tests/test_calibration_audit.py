import pytest
import pandas as pd
import numpy as np
from copy import deepcopy

from config.loader import load_config
from simulation.engine import DigitalTwinSimulator
from calibration.calibrator import TwinCalibrator

def test_parameter_causality():
    config = load_config('config/root.yaml')
    
    # Restrict to a very short simulation for speed (12 hours)
    config.simulation.end_datetime = config.simulation.start_datetime + pd.Timedelta(hours=12)
    
    sim_base = DigitalTwinSimulator(config)
    df_base = sim_base.simulate()
    
    # 1. Base Load Causality
    cfg_pwr = deepcopy(config)
    target_room = cfg_pwr.campus.buildings[0].floors[0].rooms[0]
    target_room.power.base_load_kw *= 1.5
    df_pwr = DigitalTwinSimulator(cfg_pwr).simulate()
    assert not np.allclose(df_base['reported_power_kw'].values, df_pwr['reported_power_kw'].values)
    
    # 2. Thermal Resistance Causality
    cfg_thm = deepcopy(config)
    target_room = cfg_thm.campus.buildings[0].floors[0].rooms[0]
    target_room.temperature.thermal_resistance_c_w *= 1.5
    df_thm = DigitalTwinSimulator(cfg_thm).simulate()
    assert not np.allclose(df_base['reported_temperature_c'].values, df_thm['reported_temperature_c'].values)
    
    # 3. Ventilation Rate Causality
    cfg_co2 = deepcopy(config)
    target_room = cfg_co2.campus.buildings[0].floors[0].rooms[0]
    target_room.co2.ventilation_rate_m3_s *= 1.5
    df_co2 = DigitalTwinSimulator(cfg_co2).simulate()
    assert not np.allclose(df_base['reported_co2_ppm'].values, df_co2['reported_co2_ppm'].values)

from unittest.mock import patch

def test_synthetic_recovery():
    # 1. Generate True Data
    config_true = load_config('config/root.yaml')
    config_true.simulation.end_datetime = config_true.simulation.start_datetime + pd.Timedelta(days=1)
    target_room = config_true.campus.buildings[0].floors[0].rooms[0]
    
    # Disable HVAC to make base load identifiable from total power
    target_room.hvac.cooling_capacity_kw = 0.0
    
    # Define Ground Truth
    true_base_load = target_room.power.base_load_kw
    
    # Fix the simulator PRNG seed so changes to config parameters don't randomize occupancy
    with patch('simulation.engine.hashlib.md5') as mock_md5:
        class FakeHash:
            def hexdigest(self): return "12345678"
        mock_md5.return_value = FakeHash()
        
        sim_true = DigitalTwinSimulator(config_true)
        df_true = sim_true.simulate()
        
        # Convert simulation output to "real" dataset format for the calibrator
        # We drop temperature and CO2 to isolate power optimization and avoid collinear heat-transfer trade-offs
        df_real = df_true[['timestamp', 'location_id', 'reported_power_kw', 'occupancy']].copy()
        df_real['timestamp'] = pd.to_datetime(df_real['timestamp'], utc=True)
        
        # 2. Create Perturbed Config (Initial Guess)
        config_perturbed = deepcopy(config_true)
        perturbed_room = config_perturbed.campus.buildings[0].floors[0].rooms[0]
        perturbed_room.power.base_load_kw = true_base_load + 0.5  # Deliberately offset
        
        # 3. Calibrate
        # We use L-BFGS-B here because for power alone (HVAC disabled), the surface is smooth and convex
        calibrator = TwinCalibrator(config_perturbed, method='L-BFGS-B')
        # Use a small subset
        cal_config, val_df = calibrator.calibrate(df_real, target_room_id=target_room.id, bld_id=config_true.campus.buildings[0].id, train_ratio=0.7)
    
    # 4. Check Convergence
    opt_params = calibrator.report['optimized_parameters']
    
    # Power loads can be collinear (base + lighting). The total load should be recovered.
    true_total_power = true_base_load + target_room.power.lighting_capacity_kw
    opt_total_power = opt_params['base_load_kw'] + opt_params['lighting_capacity_kw']
    
    print(f"\nSYNTHETIC RECOVERY RUNTIME: {calibrator.report.get('elapsed_seconds', 0):.2f}s")
    print(f"OPTIMIZER METHOD: {calibrator.report['optimization_method']}")
    print(f"OPTIMIZER EVALUATIONS: {calibrator.report.get('evaluations', 0)}")
    print(f"INITIAL OBJ: {calibrator.report['initial_objective_value']:.4f}")
    print(f"FINAL OBJ: {calibrator.report['final_objective_value']:.4f}")
    
    assert abs(opt_total_power - true_total_power) < 0.25
    assert calibrator.report['initial_objective_value'] > calibrator.report['final_objective_value']
