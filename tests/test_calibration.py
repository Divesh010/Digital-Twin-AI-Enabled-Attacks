import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from ingestion.adapter import DatasetAdapter
from ingestion.cleaner import DataCleaner
from calibration.calibrator import TwinCalibrator
from calibration.validator import TwinValidator
from config.loader import load_config
import os

@pytest.fixture
def mock_dataset():
    times = [datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(24)]
    df = pd.DataFrame({
        'dt': times,
        'bldg': ['academic_block'] * 24,
        'rm': ['A101'] * 24,
        'energy_val': np.random.uniform(1.0, 5.0, 24),
        'temp_c': np.random.uniform(20.0, 25.0, 24),
        'co2': np.random.uniform(400, 800, 24),
        'occ': np.random.randint(0, 10, 24)
    })
    return df

def test_ingestion_adapter(mock_dataset):
    mapping = {
        'timestamp': 'dt',
        'university_id': '__STATIC__TestUniv',
        'campus_id': '__STATIC__TestCampus',
        'building_id': 'bldg',
        'room_id': 'rm',
        'energy_kwh': 'energy_val',
        'temperature_c': 'temp_c',
        'co2_ppm': 'co2',
        'occupancy': 'occ',
        'delta_t_hours': 1.0
    }
    adapter = DatasetAdapter(mapping)
    canonical = adapter.apply(mock_dataset)
    
    assert 'timestamp' in canonical.columns
    assert 'reported_power_kw' in canonical.columns
    assert 'reported_temperature_c' in canonical.columns
    assert (canonical['university_id'] == 'TestUniv').all()
    assert (canonical['reported_power_kw'] == canonical['energy_interval_kwh']).all() # since delta_t_hours=1

def test_data_cleaner(mock_dataset):
    mapping = {
        'timestamp': 'dt',
        'building_id': 'bldg',
        'room_id': 'rm',
        'temperature_c': 'temp_c'
    }
    adapter = DatasetAdapter(mapping)
    canonical = adapter.apply(mock_dataset)
    
    # Introduce bad data
    canonical.loc[0, 'reported_temperature_c'] = -100 # impossible
    
    cleaner = DataCleaner()
    clean_df, report = cleaner.clean(canonical)
    
    assert pd.isna(clean_df.loc[0, 'reported_temperature_c'])
    assert report['final_records'] == 24

def test_calibration_pipeline(mock_dataset, tmp_path):
    mapping = {
        'timestamp': 'dt',
        'university_id': '__STATIC__bennett_uni',
        'campus_id': '__STATIC__main_campus',
        'building_id': 'bldg',
        'floor_id': '__STATIC__floor_1',
        'room_id': 'rm',
        'energy_kwh': 'energy_val',
        'temperature_c': 'temp_c',
        'co2_ppm': 'co2',
        'delta_t_hours': 1.0
    }
    
    canonical = DatasetAdapter(mapping).apply(mock_dataset)
    clean_df, _ = DataCleaner().clean(canonical)
    
    config = load_config('config/root.yaml')
    calibrator = TwinCalibrator(config, method='Powell')
    
    cal_config, val_df = calibrator.calibrate(clean_df, target_room_id='A101', bld_id='academic_block', train_ratio=0.5)
    
    assert calibrator.report['optimization_status'].startswith('SUCCESS')
    assert 'base_load_kw' in calibrator.report['optimized_parameters']
    
    # Validation
    val_config = cal_config
    val_config.simulation.start_datetime = val_df['timestamp'].min()
    val_config.simulation.end_datetime = val_df['timestamp'].max()
    
    validator = TwinValidator(val_config)
    metrics = validator.validate(val_df, str(tmp_path))
    
    assert 'Power' in metrics
    assert 'Temperature' in metrics
    assert os.path.exists(tmp_path / 'metrics.csv')
    assert os.path.exists(tmp_path / 'actual_vs_simulated_Power.png')
