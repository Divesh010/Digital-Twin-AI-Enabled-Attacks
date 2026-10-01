import os, re
path = r'C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\06_Building_Reports.py'
with open(path, 'r', encoding='utf-8') as f:
    t = f.read()

# Add import
t = t.replace('from dashboard.data.loader import load_historical_data, get_hierarchy', 
              'from dashboard.data.loader import load_historical_data, get_hierarchy\nfrom dashboard.data.campus_config import load_campus_layout')

# Replace buildings list logic
t = t.replace("buildings = df['building_id'].unique().tolist()", 
"""# Get buildings from config and telemetry
layout = load_campus_layout()
config_blds = [b.get("id") for b in layout.get("buildings", []) if b.get("id")]
telemetry_blds = df['building_id'].unique().tolist()
buildings = sorted(list(set(config_blds + telemetry_blds)))""")

with open(path, 'w', encoding='utf-8') as f:
    f.write(t)
print('Fixed 06_Building_Reports')
