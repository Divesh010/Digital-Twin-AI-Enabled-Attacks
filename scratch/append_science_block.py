import yaml
with open('config/campus.yaml', 'r') as f:
    data = yaml.safe_load(f)

science_block = {
    'id': 'science_block',
    'floors': [
        {
            'id': 'floor_1',
            'rooms': [
                {
                    'id': 'S101',
                    'capacity': 60,
                    'volume_m3': 150.0,
                    'schedule_id': 'weekday_class',
                    'co2': {'generation_rate_m3_s_person': 0.000005, 'ventilation_rate_m3_s': 0.1},
                    'temperature': {'thermal_mass_j_c': 1200000.0, 'thermal_resistance_c_w': 0.02, 'heat_per_person_w': 100.0},
                    'hvac': {'cooling_capacity_kw': 10.0, 'cop': 3.0, 'setpoint_c': 24.0},
                    'power': {'base_load_kw': 0.2, 'lighting_capacity_kw': 1.2}
                }
            ]
        },
        {
            'id': 'floor_2',
            'rooms': []
        },
        {
            'id': 'floor_3',
            'rooms': []
        }
    ]
}

# Only append if not exists
if not any(b['id'] == 'science_block' for b in data['buildings']):
    data['buildings'].append(science_block)

with open('config/campus.yaml', 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

print("Science Block appended.")
