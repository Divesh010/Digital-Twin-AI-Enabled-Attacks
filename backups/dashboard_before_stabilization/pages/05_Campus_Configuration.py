import textwrap
import streamlit as st
import yaml
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from pathlib import Path
from dashboard.styles import DARK_THEME_CSS, flatten_html, section_header, kpi_card
st.set_page_config(page_title='Campus Configuration', page_icon='⚙️', layout='wide', initial_sidebar_state='expanded')
st.markdown(flatten_html(DARK_THEME_CSS), unsafe_allow_html=True)
st.markdown(flatten_html(section_header('CAMPUS CONFIGURATION & TOPOLOGY', '⚙️')), unsafe_allow_html=True)
CONFIG_PATH = Path(os.path.join(os.path.dirname(__file__), '../../../config/campus.yaml')).resolve()

def load_campus_config():
    if not CONFIG_PATH.exists():
        return {'id': 'main_campus', 'buildings': []}
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_campus_config(config_data):
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
if 'campus_config' not in st.session_state:
    st.session_state.campus_config = load_campus_config()
config = st.session_state.campus_config
buildings = config.get('buildings', [])
MAX_BUILDINGS = 16
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(flatten_html(kpi_card('Total Buildings', str(len(buildings)), f'/ {MAX_BUILDINGS} Max', '#00bcd4', '🏢')), unsafe_allow_html=True)
with col2:
    total_floors = sum((len(b.get('floors', [])) for b in buildings))
    st.markdown(flatten_html(kpi_card('Total Floors', str(total_floors), '', '#4caf50', '🏢')), unsafe_allow_html=True)
with col3:
    total_rooms = sum((len(f.get('rooms', [])) for b in buildings for f in b.get('floors', [])))
    st.markdown(flatten_html(kpi_card('Total Rooms', str(total_rooms), '', '#ff9800', '🚪')), unsafe_allow_html=True)
st.markdown(flatten_html('---'), unsafe_allow_html=True)
st.subheader('➕ Add New Building')
if len(buildings) >= MAX_BUILDINGS:
    st.warning(f'Maximum limit of {MAX_BUILDINGS} buildings reached. You cannot add more buildings according to the university architecture limits.')
else:
    with st.form('add_building_form'):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_bld_id = st.text_input('Building ID (e.g., science_block)', key='new_bld')
        with col2:
            num_floors = st.number_input('Number of Floors', min_value=1, max_value=10, value=2)
        with col3:
            rooms_per_floor = st.number_input('Rooms per Floor', min_value=1, max_value=20, value=3)
        submitted = st.form_submit_button('Create Building')
        if submitted:
            if not new_bld_id or ' ' in new_bld_id:
                st.error('Building ID must not be empty and cannot contain spaces (use underscores).')
            elif any((b['id'] == new_bld_id for b in buildings)):
                st.error(f"Building '{new_bld_id}' already exists!")
            else:
                new_building = {'id': new_bld_id, 'floors': []}
                for f in range(1, num_floors + 1):
                    floor_id = f'floor_{f}'
                    floor_data = {'id': floor_id, 'rooms': []}
                    for r in range(1, rooms_per_floor + 1):
                        room_id = f'R{f}{r:02d}'
                        room_data = {'id': room_id, 'capacity': 30, 'volume_m3': 75.0, 'schedule_id': 'weekday_class', 'co2': {'generation_rate_m3_s_person': 5e-06, 'ventilation_rate_m3_s': 0.05}, 'temperature': {'thermal_mass_j_c': 600000.0, 'thermal_resistance_c_w': 0.02, 'heat_per_person_w': 100.0}, 'hvac': {'cooling_capacity_kw': 5.0, 'cop': 3.0, 'setpoint_c': 24.0}, 'power': {'base_load_kw': 0.1, 'lighting_capacity_kw': 0.6}}
                        floor_data['rooms'].append(room_data)
                    new_building['floors'].append(floor_data)
                config['buildings'].append(new_building)
                save_campus_config(config)
                st.session_state.campus_config = config
                st.success(f"Building '{new_bld_id}' added successfully!")
                st.rerun()
st.markdown(flatten_html('---'), unsafe_allow_html=True)
st.subheader('🏢 Current University Architecture')
for i, bld in enumerate(buildings):
    with st.expander(f"Building: {bld['id']} ({len(bld.get('floors', []))} floors)"):
        c1, c2 = st.columns([4, 1])
        with c1:
            for floor in bld.get('floors', []):
                rooms = floor.get('rooms', [])
                st.write(f"**{floor['id']}**: {len(rooms)} rooms ({', '.join([r['id'] for r in rooms])})")
        with c2:
            if st.button('🗑️ Delete', key=f"del_{bld['id']}"):
                config['buildings'].pop(i)
                save_campus_config(config)
                st.session_state.campus_config = config
                st.rerun()
st.info('Note: Any changes to the architecture will require you to re-run the simulation script (`scripts/generate_data.py`) to generate matching telemetry for the new buildings.')