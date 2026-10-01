import textwrap
import streamlit as st

import pandas as pd

import plotly.graph_objects as go

from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry

from dashboard.styles import (

    DARK_THEME_CSS, render_header, flatten_html, section_header, kpi_card,

    status_indicator, PLOTLY_DARK_TEMPLATE

)



st.set_page_config(page_title="Security Dashboard", page_icon="BU", layout="wide", initial_sidebar_state="expanded")

st.markdown(flatten_html(DARK_THEME_CSS), unsafe_allow_html=True)



df = load_historical_data()

if df.empty:

    st.error("No data available.")

    st.stop()



config = load_app_config()

mqtt_connected = (

    st.session_state.get('mqtt_client') is not None

    and st.session_state.mqtt_client.is_connected

)

if mqtt_connected:

    live_df = st.session_state.mqtt_client.get_latest_data()

    if not live_df.empty:

        df = pd.concat([df, live_df], ignore_index=True)

df = deduplicate_telemetry(df)



last_ts = df['timestamp'].max().strftime("%Y-%m-%d %H:%M")

render_header(mqtt_connected=mqtt_connected, record_count=len(df), last_update=last_ts)



st.markdown(flatten_html(section_header("CYBERSECURITY & FDI MONITORING", "🛡️")), unsafe_allow_html=True)



st.markdown(flatten_html("""

<div style="background: #151c25; border: 1px solid #2a3441; border-radius: 2px; padding: 12px 16px; margin-bottom: 12px;">

    <div style="font-size: 11px; color: #9aa0a6; line-height: 1.6;">

        <b style="color: #e8eaed;">Ground-Truth Attack Visualization.</b>

        This dashboard shows the actual FDI attack labels injected by the Phase 6B engine.

        No ML detection algorithm is active. The TRUE, OBSERVED, and REPORTED telemetry layers are displayed

        to evaluate the impact of False Data Injection attacks on downstream telemetry integrity.

    </div>

</div>

"""), unsafe_allow_html=True)



manipulated_df = df[df['is_manipulated'] == True]

total_records = len(df)

manipulated_count = len(manipulated_df)

attacked_locations = manipulated_df['location_id'].unique() if not manipulated_df.empty else []

attack_count = manipulated_df['attack_id'].nunique() if 'attack_id' in manipulated_df.columns and not manipulated_df.empty else 0



# Threat level

if len(attacked_locations) == 0:

    threat_level = "NORMAL"

    threat_color = "#4caf50"

    threat_bg = "rgba(76,175,80,0.1)"

elif len(attacked_locations) <= 1:

    threat_level = "WARNING"

    threat_color = "#ff9800"

    threat_bg = "rgba(255,152,0,0.1)"

else:

    threat_level = "CRITICAL"

    threat_color = "#f44336"

    threat_bg = "rgba(244,67,54,0.1)"



# Threat level banner

st.markdown(flatten_html(f"""

<div style="

    background: {threat_bg};

    border: 2px solid {threat_color};

    border-radius: 2px;

    padding: 16px 24px;

    margin-bottom: 16px;

    display: flex;

    align-items: center;

    justify-content: space-between;

">

    <div style="display: flex; align-items: center; gap: 16px;">

        <div style="

            width: 50px; height: 50px;

            border: 2px solid {threat_color};

            border-radius: 50%;

            display: flex; align-items: center; justify-content: center;

            font-size: 24px;

        ">🛡️</div>

        <div>

            <div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px;">Threat Level</div>

            <div style="font-size: 22px; color: {threat_color}; font-weight: 800;">{threat_level}</div>

        </div>

    </div>

    <div style="display: flex; gap: 32px;">

        <div style="text-align: center;">

            <div style="font-size: 9px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px;">Total Records</div>

            <div style="font-size: 18px; color: #e8eaed; font-weight: 700;">{total_records:,}</div>

        </div>

        <div style="text-align: center;">

            <div style="font-size: 9px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px;">Manipulated</div>

            <div style="font-size: 18px; color: {threat_color}; font-weight: 700;">{manipulated_count:,}</div>

        </div>

        <div style="text-align: center;">

            <div style="font-size: 9px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px;">FDI Attacks</div>

            <div style="font-size: 18px; color: #ff9800; font-weight: 700;">{attack_count}</div>

        </div>

        <div style="text-align: center;">

            <div style="font-size: 9px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px;">Affected Rooms</div>

            <div style="font-size: 18px; color: {threat_color}; font-weight: 700;">{len(attacked_locations)}</div>

        </div>

    </div>

</div>

"""), unsafe_allow_html=True)



if manipulated_df.empty:

    st.markdown(flatten_html("""

    <div style="text-align: center; padding: 40px; color: #4caf50; font-size: 16px;">

        <div style="font-size: 48px; margin-bottom: 12px;">✓</div>

        <div>No active FDI attacks detected in the current dataset.</div>

    </div>

    """), unsafe_allow_html=True)

    st.stop()



# Attack summary cards

st.markdown(flatten_html(section_header("ATTACK REGISTRY", "📋")), unsafe_allow_html=True)



attack_ids = manipulated_df['attack_id'].dropna().unique()

for atk_id in attack_ids:

    atk_df = manipulated_df[manipulated_df['attack_id'] == atk_id]

    atk_row = atk_df.iloc[0]

    atk_type = atk_row.get('attack_type', 'UNKNOWN')

    atk_target = atk_row.get('attack_target', 'UNKNOWN')

    atk_location = atk_row.get('location_id', 'UNKNOWN')

    atk_room = atk_row.get('room_id', 'UNKNOWN')

    atk_start = atk_row.get('attack_start', 'UNKNOWN')

    atk_end = atk_row.get('attack_end', 'UNKNOWN')



    type_colors = {'OFFSET': '#f44336', 'SLOW_DRIP': '#ff9800', 'REPLAY': '#9c27b0'}

    type_color = type_colors.get(atk_type, '#9aa0a6')



    st.markdown(flatten_html(f"""

    <div style="background: #151c25; border: 1px solid #2a3441; border-left: 4px solid {type_color}; border-radius: 2px; padding: 12px 16px; margin: 6px 0;">

        <div style="display: flex; justify-content: space-between; align-items: center;">

            <div>

                <span style="font-size: 13px; color: #e8eaed; font-weight: 700;">{atk_id}</span>

                <span style="background: {type_color}; color: white; font-size: 9px; font-weight: 700; padding: 2px 8px; border-radius: 2px; margin-left: 8px; text-transform: uppercase;">{atk_type}</span>

            </div>

            <div style="font-size: 11px; color: #9aa0a6;">

                Room: <b style="color: #e8eaed;">{atk_room}</b>

            </div>

        </div>

        <div style="font-size: 10px; color: #9aa0a6; margin-top: 6px;">

            Target: <b style="color: #e8eaed;">{atk_target}</b> &bull;

            Window: <b style="color: #e8eaed;">{atk_start}</b> → <b style="color: #e8eaed;">{atk_end}</b> &bull;

            Records: <b style="color: #e8eaed;">{len(atk_df)}</b>

        </div>

    </div>

    """), unsafe_allow_html=True)



# Detailed attack visualization

st.markdown(flatten_html(section_header("ATTACK ANALYSIS", "🔍")), unsafe_allow_html=True)



selected_location = st.selectbox("Select Attacked Room (Location ID)", attacked_locations, label_visibility="collapsed")



room_df = df[df['location_id'] == selected_location].copy()

room_attacks = room_df[room_df['is_manipulated'] == True]

attack_metadata = room_attacks.iloc[-1]



target_var = attack_metadata.get('attack_target', 'reported_co2_ppm')

obs_var = target_var.replace('reported_', 'observed_')

true_var = target_var.replace('reported_', 'true_')



# Three-layer comparison chart

fig = go.Figure()



if true_var in room_df.columns:

    fig.add_trace(go.Scatter(

        x=room_df['timestamp'], y=room_df[true_var],

        mode='lines', name='TRUE (Physical)',

        line=dict(dash='dash', color='#9aa0a6', width=1)

    ))



if obs_var in room_df.columns:

    fig.add_trace(go.Scatter(

        x=room_df['timestamp'], y=room_df[obs_var],

        mode='lines', name='OBSERVED (Sensor)',

        line=dict(color='#2196f3', width=1.5)

    ))



if target_var in room_df.columns:

    fig.add_trace(go.Scatter(

        x=room_df['timestamp'], y=room_df[target_var],

        mode='lines', name='MANIPULATED REPORTED (FDI Corrupted)',

        line=dict(color='#f44336', width=2)

    ))



# Attack window highlighting

if not room_attacks.empty:

    start_ts = pd.to_datetime(attack_metadata.get('attack_start', room_attacks['timestamp'].min()))

    end_ts = pd.to_datetime(attack_metadata.get('attack_end', room_attacks['timestamp'].max()))

    fig.add_vrect(

        x0=start_ts, x1=end_ts,

        fillcolor="rgba(244,67,54,0.15)", layer="below", line_width=0,

        annotation_text="FDI ATTACK WINDOW", annotation_position="top left",

        annotation=dict(font=dict(color="#f44336", size=10))

    )



attack_type = attack_metadata.get('attack_type', 'UNKNOWN')

fig.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

fig.update_layout(

    title=dict(

        text=f'FDI ANALYSIS: {attack_type} on {target_var} ({selected_location.split(".")[-1]})',

        font=dict(size=13, color='#e8eaed')

    ),

    yaxis_title=target_var.split('_')[-1].upper(),

    height=350, hovermode='x unified',

    

)

st.plotly_chart(fig, use_container_width=True)



# Attack magnitude over time

if 'attack_magnitude' in room_attacks.columns:

    st.markdown(flatten_html(section_header("ATTACK MAGNITUDE OVER TIME", "📊")), unsafe_allow_html=True)

    fig_mag = go.Figure()

    fig_mag.add_trace(go.Scatter(

        x=room_attacks['timestamp'],

        y=pd.to_numeric(room_attacks['attack_magnitude'], errors='coerce'),

        mode='lines+markers', name='Attack Magnitude',

        line=dict(color='#f44336', width=2),

        marker=dict(size=4, color='#f44336')

    ))

    fig_mag.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

    fig_mag.update_layout(

        title=dict(text='INJECTION MAGNITUDE', font=dict(size=12, color='#9aa0a6')),

        yaxis_title='Magnitude', height=250,

        

    )

    st.plotly_chart(fig_mag, use_container_width=True)



# Raw logs

with st.expander("RAW ATTACK LOGS"):

    cols_show = ['timestamp', 'location_id', 'attack_id', 'attack_type', 'attack_target', obs_var, target_var, 'attack_magnitude']

    avail_cols = [c for c in cols_show if c in room_attacks.columns]

    st.dataframe(room_attacks[avail_cols], use_container_width=True)