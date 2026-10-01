import os
import subprocess
import time

STAGES = {
    "C1": """import streamlit as st
import yaml

st.set_page_config(page_title="Campus Configuration", layout="wide")
st.title("CONFIG CANARY")
st.write("Configuration page is rendering.")
""",
    "C2": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")
st.title("CONFIG CANARY C2")
""",
    "C3": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")
st.title("CONFIG CANARY C3")
try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])
st.write(f"Loaded {len(buildings)} buildings.")
""",
    "C4": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")

try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])

st.header("UNIVERSITY IDENTITY")
id_col1, id_col2 = st.columns(2)
with id_col1:
    uni_id = st.text_input("University ID", value=layout.get("university_id", "bu"), key="uni_id")
""",
    "C5": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")
try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])

st.header("UNIVERSITY IDENTITY")
id_col1, id_col2 = st.columns(2)
with id_col1:
    uni_id = st.text_input("University ID", value=layout.get("university_id", "bu"), key="uni_id")
    campus_id = st.text_input("Campus ID", value=layout.get("campus_id", "main_campus"), key="campus_id")
with id_col2:
    uni_name = st.text_input("University Name", value=layout.get("university_name", "Bennett University"), key="uni_name")
    campus_name = st.text_input("Campus Name", value=layout.get("campus_name", "Main Campus"), key="campus_name")
""",
    "C6": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path
from dashboard.styles import kpi_card

st.set_page_config(page_title="Campus Configuration", layout="wide")
try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])

c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Total Buildings", str(len(buildings)), f"/ {MAX_BUILDINGS} Max", "#00bcd4", "")
with c2:
    total_floors = sum(b.get("num_floors", 0) for b in buildings)
    kpi_card("Total Floors", str(total_floors), "", "#4caf50", "")
with c3:
    kpi_card("Config Status", "SAVED" if get_config_path().exists() else "MISSING", "", "#ff9800", "")
""",
    "C7": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")
try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])

st.header("ADD NEW BUILDING")
with st.form("add_building_form", clear_on_submit=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        new_bld_id = st.text_input("Building ID")
    with fc2:
        new_bld_name = st.text_input("Building Name")
    with fc3:
        new_num_floors = st.number_input("Floors", min_value=1, max_value=20, value=2)

    submitted = st.form_submit_button("Add Building", type="primary")
    if submitted:
        st.write("Submitted!")
""",
    "C8": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")
try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])

if not buildings:
    st.info("No buildings configured.")
else:
    for i, bld in enumerate(buildings):
        bld_id = bld.get("id", f"building_{i}")
        bld_name = bld.get("name", bld_id.replace("_", " ").title())
        bld_floors = bld.get("num_floors", 0)

        with st.expander(f"{bld_name} ID: `{bld_id}` {bld_floors} floor(s)", expanded=False):
            ec1, ec2, ec3 = st.columns([2, 2, 1])
            with ec1:
                st.markdown(f"**Building ID:** `{bld_id}`")
            with ec2:
                st.markdown(f"**Floors:** {bld_floors}")
            with ec3:
                if st.button("Delete", key=f"del_{bld_id}_{i}"):
                    buildings.pop(i)
                    layout["buildings"] = buildings
                    st.rerun()
""",
    "C9": """import streamlit as st
import yaml
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")
try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])

if st.button("SAVE CONFIGURATION", type="primary", width="stretch"):
    layout["buildings"] = buildings
    try:
        save_campus_layout(layout)
        st.success(f"Configuration saved.")
    except ValueError as ve:
        st.error(str(ve))
""",
    "C10": """import streamlit as st
import yaml
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card, PLOTLY_DARK_TEMPLATE
)
from dashboard.data.campus_config import load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path

st.set_page_config(page_title="Campus Configuration", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
render_header(mqtt_connected=False, record_count=0, last_update="--")

try:
    layout = load_campus_layout()
except Exception:
    layout = {}
buildings = layout.get("buildings", [])

section_header("CAMPUS CONFIGURATION & TOPOLOGY", "")
"""
}

TARGET_FILE = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\05_Campus_Configuration.py"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Campus Configuration"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

for stage_name, stage_code in STAGES.items():
    print(f"\\n{'='*50}\\nRUNNING {stage_name}\\n{'='*50}")
    
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(stage_code)
        
    print(f"Wrote {stage_name} to {TARGET_FILE}. Starting Electron...")
    
    process = subprocess.Popen(
        ["npm.cmd", "--prefix", "desktop", "start"], 
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if line:
            print(line)
        if "[TEST] Sequence complete" in line or "[RENDER-GONE]" in line or "Error executing JS" in line or "[FAIL-LOAD]" in line:
            break
            
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    time.sleep(2)
