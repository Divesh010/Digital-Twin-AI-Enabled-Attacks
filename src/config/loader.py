import yaml
from yaml.error import YAMLError
from pathlib import Path
from typing import Dict, Any
from .models import RootConfig

def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return yaml.safe_load(f)
        except YAMLError as e:
            raise ValueError(f"Malformed YAML in {path}: {e}")

def load_config(root_path: str) -> RootConfig:
    """Loads and merges all configuration files into a validated RootConfig."""
    root_file = Path(root_path)
    root_data = load_yaml(root_file)

    base_dir = root_file.parent
    
    try:
        campus_data = load_yaml(base_dir / root_data.get('campus_file', 'campus.yaml'))
        schedules_data = load_yaml(base_dir / root_data.get('schedules_file', 'schedules.yaml'))
        physics_data = load_yaml(base_dir / root_data.get('physics_file', 'physics.yaml'))
        simulation_data = load_yaml(base_dir / root_data.get('simulation_file', 'simulation.yaml'))
    except FileNotFoundError as e:
        raise ValueError(f"Missing required configuration component: {e}")

    scenarios_file = base_dir / root_data.get('scenarios_file', 'scenarios.yaml')
    scenarios_data = load_yaml(scenarios_file) if scenarios_file.exists() else []
    
    calibration_file = base_dir / root_data.get('calibration_file', 'calibration.yaml')
    calibration_data = load_yaml(calibration_file) if calibration_file.exists() else {}
    
    mqtt_file = base_dir / root_data.get('mqtt_file', 'mqtt.yaml')
    mqtt_data = load_yaml(mqtt_file) if mqtt_file.exists() else {}

    attacks_file = base_dir / root_data.get('attacks_file', 'attacks.yaml')
    attacks_data = load_yaml(attacks_file) if attacks_file.exists() else []

    merged_data = {
        'campus': campus_data,
        'schedules': schedules_data,
        'physics': physics_data,
        'simulation': simulation_data,
        'scenarios': scenarios_data,
        'calibration': calibration_data,
        'mqtt': mqtt_data,
        'attacks': attacks_data,
        'model_version': root_data.get('model_version', 'v1.0.0')
    }

    try:
        return RootConfig(**merged_data)
    except Exception as e:
        raise ValueError(f"Configuration validation failed:\n{e}")

