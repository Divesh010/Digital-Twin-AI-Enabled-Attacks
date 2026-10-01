import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
import yaml
from pathlib import Path
from config.models import RootConfig

def test_root_config_fdi_validation():
    from config.loader import load_yaml
    base_dir = Path("config")
    root_data = load_yaml(base_dir / "root.yaml")
    
    campus_data = load_yaml(base_dir / root_data.get('campus_file', 'campus.yaml'))
    physics_data = load_yaml(base_dir / root_data.get('physics_file', 'physics.yaml'))
    sim_data = load_yaml(base_dir / root_data.get('simulation_file', 'simulation.yaml'))
    schedules_data = load_yaml(base_dir / root_data.get('schedules_file', 'schedules.yaml'))
    scenarios_data = load_yaml(base_dir / root_data.get('scenarios_file', 'scenarios.yaml'))
    mqtt_data = load_yaml(base_dir / root_data.get('mqtt_file', 'mqtt.yaml'))
    
    valid_attack = {
        "attack_id": "VALID_ATTACK",
        "enabled": True,
        "target_location": "bennett_uni.main_campus.academic_block.floor_1.A101",
        "target_variable": "reported_co2_ppm",
        "start_time": "2026-09-02T10:00:00Z",
        "end_time": "2026-09-02T12:00:00Z",
        "parameters": {"attack_type": "OFFSET", "offset_value": 100.0}
    }
    
    config_dict = {
        'campus': campus_data, 'schedules': schedules_data, 'physics': physics_data,
        'simulation': sim_data, 'scenarios': scenarios_data, 'mqtt': mqtt_data,
        'attacks': [valid_attack]
    }
    
    config = RootConfig(**config_dict)
    assert len(config.attacks) == 1
    
    dup_attack = valid_attack.copy()
    config_dict['attacks'] = [valid_attack, dup_attack]
    with pytest.raises(ValidationError) as exc:
        RootConfig(**config_dict)
    assert "Duplicate attack_id" in str(exc.value)
    
    invalid_loc = valid_attack.copy()
    invalid_loc["attack_id"] = "INVALID_LOC"
    invalid_loc["target_location"] = "bennett_uni.main_campus.academic_block.floor_1.NONEXISTENT_ROOM"
    config_dict['attacks'] = [invalid_loc]
    with pytest.raises(ValidationError) as exc:
        RootConfig(**config_dict)
    assert "Invalid FDI target_location" in str(exc.value)
