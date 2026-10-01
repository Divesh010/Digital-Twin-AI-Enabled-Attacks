import streamlit as st
run_count = st.session_state.get('_debug_run_count', 0) + 1
st.session_state['_debug_run_count'] = run_count
st.write(f'DEBUG PAGE RUN = {run_count}')
print(f'[DEBUG] Dashboard execution #{run_count}', flush=True)
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", page_icon="BU", layout="wide", initial_sidebar_state="expanded")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

df = load_historical_data()
config = load_app_config()

mqtt_connected = False
if 'mqtt_client' in st.session_state and getattr(st.session_state.mqtt_client, 'connected', False):
    mqtt_connected = True

if not df.empty:
    df = deduplicate_telemetry(df)
    last_ts = df['timestamp'].max().strftime("%Y-%m-%d %H:%M")
    record_count = len(df)
else:
    last_ts = "--"
    record_count = 0

render_header(mqtt_connected=mqtt_connected, record_count=record_count, last_update=last_ts)

section_header("CYBERSECURITY & FDI MONITORING", "🛡️")

st.info(
    "**Ground-Truth Attack Visualization.** "
    "This dashboard shows the actual FDI attack labels injected by the Phase 6B engine. "
    "No ML detection algorithm is active. The TRUE, OBSERVED, and REPORTED telemetry layers are displayed "
    "to evaluate the impact of False Data Injection attacks on downstream telemetry integrity."
)

# ========== ATTACK DETECTION ==========
manipulated_df = df[df['is_manipulated'] == True].copy() if not df.empty and 'is_manipulated' in df.columns else pd.DataFrame()
total_records = len(df)
manipulated_count = len(manipulated_df)
attacked_locations = manipulated_df['location_id'].unique().tolist() if not manipulated_df.empty else []
attack_count = manipulated_df['attack_id'].nunique() if 'attack_id' in manipulated_df.columns and not manipulated_df.empty else 0

# Threat level
if len(attacked_locations) == 0:
    threat_level = "NORMAL"
elif len(attacked_locations) <= 1:
    threat_level = "WARNING"
else:
    threat_level = "CRITICAL"

# ========== THREAT SUMMARY ==========
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

# ========== NO ATTACK CASE ==========
if df.empty:
    st.warning("No historical telemetry is currently available. Waiting for data ingestion...")
elif manipulated_df.empty:
    st.success("No active FDI attacks detected in the current dataset.")
else:
    st.warning(f"{manipulated_count} records show signs of FDI manipulation.")

# ========== ATTACK REGISTRY ==========
section_header("ATTACK REGISTRY", "📋")

if not manipulated_df.empty and 'attack_id' in manipulated_df.columns:
    attack_ids = manipulated_df['attack_id'].dropna().unique()
    registry_rows = []
    for atk_id in attack_ids:
        atk_df = manipulated_df[manipulated_df['attack_id'] == atk_id]
        atk_row = atk_df.iloc[0]
        registry_rows.append({
            'Attack ID': atk_id,
            'Type': atk_row.get('attack_type', 'UNKNOWN'),
            'Target Room': atk_row.get('room_id', 'UNKNOWN'),
            'Target Variable': atk_row.get('attack_target', 'UNKNOWN'),
            'Start': str(atk_row.get('attack_start', 'UNKNOWN'))[:16],
            'End': str(atk_row.get('attack_end', 'UNKNOWN'))[:16],
            'Records': len(atk_df),
        })
    if registry_rows:
        registry_df = pd.DataFrame(registry_rows)
        st.dataframe(registry_df, width='stretch', hide_index=True)
    else:
        st.info("No attack records to display.")
else:
    st.info("No FDI attacks detected. Registry is empty.")

# ========== ATTACK ANALYSIS ==========
section_header("ATTACK ANALYSIS", "🔎")

if df.empty:
    st.info("Telemetry unavailable. Cannot perform attack analysis.")
elif not attacked_locations:
    st.info("No attacked rooms to analyze. The campus is operating normally.")
else:
    selected_location = st.selectbox("Select Attacked Room (Location ID)", attacked_locations)
    room_df = df[df['location_id'] == selected_location].copy()
    room_attacks = room_df[room_df['is_manipulated'] == True]

    if room_attacks.empty:
        st.warning(f"No manipulated records found for {selected_location}.")
    else:
        attack_metadata = room_attacks.iloc[-1]
        target_var = attack_metadata.get('attack_target', 'reported_co2_ppm')
        obs_var = target_var.replace('reported_', 'observed_')
        true_var = target_var.replace('reported_', 'true_')

        fig = go.Figure()
        if true_var in room_df.columns:
            fig.add_trace(go.Scatter(x=room_df['timestamp'], y=room_df[true_var], mode='lines', name='TRUE (Physical)', line=dict(dash='dash', color='#9aa0a6', width=1)))
        if obs_var in room_df.columns:
            fig.add_trace(go.Scatter(x=room_df['timestamp'], y=room_df[obs_var], mode='lines', name='OBSERVED (Sensor)', line=dict(color='#2196f3', width=1.5)))
        if target_var in room_df.columns:
            fig.add_trace(go.Scatter(x=room_df['timestamp'], y=room_df[target_var], mode='lines', name='MANIPULATED REPORTED (FDI Corrupted)', line=dict(color='#f44336', width=2)))

        start_ts = pd.to_datetime(attack_metadata.get('attack_start', room_attacks['timestamp'].min()))
        end_ts = pd.to_datetime(attack_metadata.get('attack_end', room_attacks['timestamp'].max()))
        fig.add_vrect(x0=start_ts, x1=end_ts, fillcolor="rgba(244,67,54,0.15)", layer="below", line_width=0, annotation_text="FDI ATTACK WINDOW", annotation_position="top left", annotation=dict(font=dict(color="#f44336", size=10)))

        attack_type = attack_metadata.get('attack_type', 'UNKNOWN')
        fig.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
        fig.update_layout(title=dict(text=f'FDI ANALYSIS: {attack_type} on {target_var} ({selected_location.split(".")[-1]})', font=dict(size=13, color='#e8eaed')), yaxis_title=target_var.split('_')[-1].upper(), height=350, hovermode='x unified')
        st.plotly_chart(fig, width='stretch')

        if 'attack_magnitude' in room_attacks.columns:
            section_header("ATTACK MAGNITUDE OVER TIME", "📈")
            fig_mag = go.Figure()
            fig_mag.add_trace(go.Scatter(x=room_attacks['timestamp'], y=pd.to_numeric(room_attacks['attack_magnitude'], errors='coerce'), mode='lines+markers', name='Attack Magnitude', line=dict(color='#f44336', width=2), marker=dict(size=4, color='#f44336')))
            fig_mag.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
            fig_mag.update_layout(title=dict(text='INJECTION MAGNITUDE', font=dict(size=12, color='#9aa0a6')), yaxis_title='Magnitude', height=250)
            st.plotly_chart(fig_mag, width='stretch')

        with st.expander("RAW ATTACK LOGS"):
            cols_show = ['timestamp', 'location_id', 'attack_id', 'attack_type', 'attack_target', obs_var, target_var, 'attack_magnitude']
            avail_cols = [c for c in cols_show if c in room_attacks.columns]
            st.dataframe(room_attacks[avail_cols], width='stretch')
