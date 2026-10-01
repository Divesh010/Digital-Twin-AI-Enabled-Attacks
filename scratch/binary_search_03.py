import os
import subprocess
import time

STAGES = {
    "S1": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.title("SECURITY CANARY")
st.write("Security Dashboard is rendering.")
st.metric("Test", 123)
""",
    "S2": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
st.title("SECURITY CANARY S2")
""",
    "S3": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
render_header(mqtt_connected=False, record_count=0, last_update="--")
section_header("CYBERSECURITY & FDI MONITORING", "")
st.info("Test Info Block")
""",
    "S4": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

df = load_historical_data()
config = load_app_config()
mqtt_connected = False
if not df.empty:
    df = deduplicate_telemetry(df)
    last_ts = df['timestamp'].max().strftime("%Y-%m-%d %H:%M")
    record_count = len(df)
else:
    last_ts = "--"
    record_count = 0

render_header(mqtt_connected=mqtt_connected, record_count=record_count, last_update=last_ts)
section_header("CYBERSECURITY & FDI MONITORING", "")
st.info("Telemetry loaded.")
""",
    "S5": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

df = load_historical_data()
config = load_app_config()
mqtt_connected = False
if not df.empty:
    df = deduplicate_telemetry(df)
    last_ts = df['timestamp'].max().strftime("%Y-%m-%d %H:%M")
    record_count = len(df)
else:
    last_ts = "--"
    record_count = 0

render_header(mqtt_connected=mqtt_connected, record_count=record_count, last_update=last_ts)
section_header("CYBERSECURITY & FDI MONITORING", "")

manipulated_df = df[df['is_manipulated'] == True].copy() if not df.empty and 'is_manipulated' in df.columns else pd.DataFrame()
total_records = len(df)
manipulated_count = len(manipulated_df)
attacked_locations = manipulated_df['location_id'].unique().tolist() if not manipulated_df.empty else []
attack_count = manipulated_df['attack_id'].nunique() if 'attack_id' in manipulated_df.columns and not manipulated_df.empty else 0

if df.empty:
    st.warning("No historical telemetry is currently available. Waiting for data ingestion...")
elif manipulated_df.empty:
    st.success("No active FDI attacks detected in the current dataset.")
else:
    st.warning(f"{manipulated_count} records show signs of FDI manipulation.")
""",
    "S6": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

df = load_historical_data()
config = load_app_config()
mqtt_connected = False
if not df.empty:
    df = deduplicate_telemetry(df)
    last_ts = df['timestamp'].max().strftime("%Y-%m-%d %H:%M")
    record_count = len(df)
else:
    last_ts = "--"
    record_count = 0

render_header(mqtt_connected=mqtt_connected, record_count=record_count, last_update=last_ts)
section_header("CYBERSECURITY & FDI MONITORING", "")

manipulated_df = df[df['is_manipulated'] == True].copy() if not df.empty and 'is_manipulated' in df.columns else pd.DataFrame()
total_records = len(df)
manipulated_count = len(manipulated_df)
attacked_locations = manipulated_df['location_id'].unique().tolist() if not manipulated_df.empty else []
attack_count = manipulated_df['attack_id'].nunique() if 'attack_id' in manipulated_df.columns and not manipulated_df.empty else 0

if len(attacked_locations) == 0:
    threat_level = "NORMAL"
elif len(attacked_locations) <= 1:
    threat_level = "WARNING"
else:
    threat_level = "CRITICAL"

with st.container(border=True):
    st.markdown(f"### Threat Level: **{threat_level}**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Records", f"{total_records:,}")
    with c2:
        st.metric("Manipulated", f"{manipulated_count:,}")
    with c3:
        st.metric("FDI Attacks", f"{attack_count}")
    with c4:
        st.metric("Affected Rooms", f"{len(attacked_locations)}")
""",
    "S7": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

df = load_historical_data()
config = load_app_config()
mqtt_connected = False
if not df.empty:
    df = deduplicate_telemetry(df)
    last_ts = df['timestamp'].max().strftime("%Y-%m-%d %H:%M")
    record_count = len(df)
else:
    last_ts = "--"
    record_count = 0

render_header(mqtt_connected=mqtt_connected, record_count=record_count, last_update=last_ts)
section_header("CYBERSECURITY & FDI MONITORING", "")

manipulated_df = df[df['is_manipulated'] == True].copy() if not df.empty and 'is_manipulated' in df.columns else pd.DataFrame()
total_records = len(df)
manipulated_count = len(manipulated_df)
attacked_locations = manipulated_df['location_id'].unique().tolist() if not manipulated_df.empty else []
attack_count = manipulated_df['attack_id'].nunique() if 'attack_id' in manipulated_df.columns and not manipulated_df.empty else 0

if len(attacked_locations) == 0:
    threat_level = "NORMAL"
else:
    threat_level = "WARNING"

with st.container(border=True):
    st.markdown(f"### Threat Level: **{threat_level}**")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Records", f"{total_records:,}")

section_header("ATTACK REGISTRY", "")
if not manipulated_df.empty and 'attack_id' in manipulated_df.columns:
    attack_ids = manipulated_df['attack_id'].dropna().unique()
    registry_rows = []
    for atk_id in attack_ids:
        atk_df = manipulated_df[manipulated_df['attack_id'] == atk_id]
        atk_row = atk_df.iloc[0]
        registry_rows.append({
            'Attack ID': atk_id,
            'Type': atk_row.get('attack_type', 'UNKNOWN'),
            'Records': len(atk_df),
        })
    if registry_rows:
        st.dataframe(pd.DataFrame(registry_rows), width='stretch', hide_index=True)
else:
    st.info("No FDI attacks detected. Registry is empty.")
""",
    "S8": """import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", layout="wide")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

df = load_historical_data()
config = load_app_config()
mqtt_connected = False
if not df.empty:
    df = deduplicate_telemetry(df)
    last_ts = df['timestamp'].max().strftime("%Y-%m-%d %H:%M")
    record_count = len(df)
else:
    last_ts = "--"
    record_count = 0

render_header(mqtt_connected=mqtt_connected, record_count=record_count, last_update=last_ts)
section_header("CYBERSECURITY & FDI MONITORING", "")

manipulated_df = df[df['is_manipulated'] == True].copy() if not df.empty and 'is_manipulated' in df.columns else pd.DataFrame()
total_records = len(df)
manipulated_count = len(manipulated_df)
attacked_locations = manipulated_df['location_id'].unique().tolist() if not manipulated_df.empty else []
attack_count = manipulated_df['attack_id'].nunique() if 'attack_id' in manipulated_df.columns and not manipulated_df.empty else 0

section_header("ATTACK ANALYSIS", "")

if df.empty:
    st.info("Telemetry unavailable. Cannot perform attack analysis.")
elif not attacked_locations:
    st.info("No attacked rooms to analyze. The campus is operating normally.")
else:
    selected_location = st.selectbox("Select Attacked Room (Location ID)", attacked_locations)
    room_df = df[df['location_id'] == selected_location].copy()
    room_attacks = room_df[room_df['is_manipulated'] == True]

    if not room_attacks.empty:
        attack_metadata = room_attacks.iloc[-1]
        target_var = attack_metadata.get('attack_target', 'reported_co2_ppm')
        obs_var = target_var.replace('reported_', 'observed_')
        true_var = target_var.replace('reported_', 'true_')

        fig = go.Figure()
        if true_var in room_df.columns:
            fig.add_trace(go.Scatter(x=room_df['timestamp'], y=room_df[true_var], mode='lines', name='TRUE'))
        if obs_var in room_df.columns:
            fig.add_trace(go.Scatter(x=room_df['timestamp'], y=room_df[obs_var], mode='lines', name='OBSERVED'))
        if target_var in room_df.columns:
            fig.add_trace(go.Scatter(x=room_df['timestamp'], y=room_df[target_var], mode='lines', name='MANIPULATED'))

        st.plotly_chart(fig, width='stretch')
"""
}

TARGET_FILE = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV['TEST_TARGET'] = 'Security Dashboard'
ENV['PYTHON_EXE'] = r'C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe'

for stage_name, stage_code in STAGES.items():
    print(f"\\n{'='*50}\\nRUNNING {stage_name}\\n{'='*50}")
    
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(stage_code)
        
    print(f"Wrote {stage_name} to {TARGET_FILE}. Starting Electron...")
    
    # Run npm start
    process = subprocess.Popen(
        ["npm.cmd", "--prefix", "desktop", "start"], 
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Read output
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if line:
            print(line)
        if "[TEST] Sequence complete" in line or "[RENDER-GONE]" in line or "Error executing JS" in line or "[FAIL-LOAD]" in line:
            break
            
    # Terminate explicitly
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    time.sleep(2)

