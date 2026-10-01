import textwrap
import streamlit as st

import pandas as pd

import plotly.graph_objects as go

from dashboard.data.loader import load_historical_data, get_hierarchy, load_app_config, deduplicate_telemetry

from dashboard.styles import (

    DARK_THEME_CSS, render_header, flatten_html, section_header, kpi_card,

    status_indicator, PLOTLY_DARK_TEMPLATE

)



st.set_page_config(page_title="Room View", page_icon="BU", layout="wide", initial_sidebar_state="expanded")

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



hierarchy = get_hierarchy(df)



# Sidebar hierarchy navigation

st.sidebar.markdown(flatten_html("""

<div style="font-size: 10px; color: #00bcd4; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; font-weight: 700;">

    Asset Navigation

</div>

"""), unsafe_allow_html=True)



campus = st.sidebar.selectbox("Campus", list(hierarchy.keys()), label_visibility="collapsed")

building = st.sidebar.selectbox("Building", list(hierarchy[campus].keys()))

floor = st.sidebar.selectbox("Floor", list(hierarchy[campus][building].keys()))

room = st.sidebar.selectbox("Room", hierarchy[campus][building][floor])



room_df = df[(df['campus_id'] == campus) & (df['building_id'] == building) & (df['floor_id'] == floor) & (df['room_id'] == room)].copy()



if room_df.empty:

    st.warning("No data found for this selection.")

    st.stop()



# Hierarchy breadcrumb

bld_name = building.replace("_", " ").title()

flr_name = floor.replace("_", " ").title()

st.markdown(flatten_html(section_header(f"ROOM: {room}  |  {bld_name} > {flr_name}", "🚪")), unsafe_allow_html=True)



st.markdown(flatten_html(f"""

<div style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">

    <div style="background: #1a222d; border: 1px solid #2a3441; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #9aa0a6;">UNIVERSITY</span> <span style="color: #e8eaed; font-weight: 600;">Bennett University</span>

    </div>

    <div style="color: #2a3441; font-size: 14px;">▸</div>

    <div style="background: #1a222d; border: 1px solid #2a3441; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #9aa0a6;">CAMPUS</span> <span style="color: #e8eaed; font-weight: 600;">{campus.replace('_',' ').title()}</span>

    </div>

    <div style="color: #2a3441; font-size: 14px;">▸</div>

    <div style="background: #1a222d; border: 1px solid #2a3441; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #9aa0a6;">BUILDING</span> <span style="color: #e8eaed; font-weight: 600;">{bld_name}</span>

    </div>

    <div style="color: #2a3441; font-size: 14px;">▸</div>

    <div style="background: #1a222d; border: 1px solid #2a3441; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #9aa0a6;">FLOOR</span> <span style="color: #e8eaed; font-weight: 600;">{flr_name}</span>

    </div>

    <div style="color: #2a3441; font-size: 14px;">▸</div>

    <div style="background: #00bcd4; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #0a0e14; font-weight: 700;">ROOM {room}</span>

    </div>

</div>

"""), unsafe_allow_html=True)



# Current state KPIs

latest = room_df.iloc[-1]

room_energy = room_df['energy_interval_kwh'].sum()

is_attacked = latest.get('is_manipulated', False)



cols = st.columns(6)

with cols[0]:

    st.markdown(flatten_html(kpi_card("Temperature", f"{latest.get('reported_temperature_c', 0):.1f}", "\u00b0C", "#00bcd4", "🌡️")), unsafe_allow_html=True)

with cols[1]:

    st.markdown(flatten_html(kpi_card("CO\u2082 Level", f"{latest.get('reported_co2_ppm', 0):.0f}", "ppm", "#009688")), unsafe_allow_html=True)

with cols[2]:

    st.markdown(flatten_html(kpi_card("Total Power", f"{latest.get('reported_power_kw', 0):.2f}", "kW", "#4caf50")), unsafe_allow_html=True)

with cols[3]:

    st.markdown(flatten_html(kpi_card("Occupancy", f"{latest.get('occupancy', 0)}", f"{latest.get('occupancy_pct', 0):.0f}%", "#2196f3")), unsafe_allow_html=True)

with cols[4]:

    hvac_color = "#ff9800" if latest.get('hvac_state', 'OFF') != 'OFF' else "#9aa0a6"

    st.markdown(flatten_html(kpi_card("HVAC State", f"{latest.get('hvac_state', 'OFF')}", f"{latest.get('hvac_power_kw', 0):.2f} kW", hvac_color)), unsafe_allow_html=True)

with cols[5]:

    st.markdown(flatten_html(kpi_card("Total Energy", f"{room_energy:,.1f}", "kWh", "#4caf50")), unsafe_allow_html=True)



# FDI status bar

if is_attacked:

    st.markdown(flatten_html(f"""

    <div style="background: rgba(244,67,54,0.15); border: 1px solid #f44336; border-radius: 2px; padding: 8px 16px; margin: 8px 0;">

        <span style="color: #f44336; font-weight: 700; font-size: 12px;">⚠ FDI ATTACK ACTIVE</span>

        <span style="color: #9aa0a6; font-size: 11px; margin-left: 16px;">

            Type: <b style="color: #e8eaed;">{latest.get('attack_type', 'N/A')}</b> |

            Target: <b style="color: #e8eaed;">{latest.get('attack_target', 'N/A')}</b> |

            Magnitude: <b style="color: #e8eaed;">{latest.get('attack_magnitude', 'N/A')}</b>

        </span>

    </div>

    """), unsafe_allow_html=True)

else:

    st.markdown(flatten_html(f"""

    <div style="background: rgba(76,175,80,0.1); border: 1px solid #4caf50; border-radius: 2px; padding: 8px 16px; margin: 8px 0;">

        <span style="color: #4caf50; font-weight: 700; font-size: 12px;">● SECURE</span>

        <span style="color: #9aa0a6; font-size: 11px; margin-left: 16px;">No active FDI attacks on this room</span>

    </div>

    """), unsafe_allow_html=True)



# Time filter

time_filter = st.selectbox("Time Window", ["Full Simulation", "Last 24 Hours", "Last 6 Hours", "Last 1 Hour"], label_visibility="collapsed")

if time_filter == "Last 24 Hours":

    room_df = room_df.tail(int(24 * 60 / 5))

elif time_filter == "Last 6 Hours":

    room_df = room_df.tail(int(6 * 60 / 5))

elif time_filter == "Last 1 Hour":

    room_df = room_df.tail(int(60 / 5))



# TRUE / OBSERVED / REPORTED chart builder

def plot_true_obs_rep(title, y_true, y_obs, y_rep, unit=""):

    fig = go.Figure()

    if y_true in room_df.columns:

        fig.add_trace(go.Scatter(

            x=room_df['timestamp'], y=room_df[y_true],

            mode='lines', name='TRUE (Physical)',

            line=dict(dash='dash', color='#9aa0a6', width=1)

        ))

    if y_obs in room_df.columns:

        fig.add_trace(go.Scatter(

            x=room_df['timestamp'], y=room_df[y_obs],

            mode='lines', name='OBSERVED (Sensor)',

            line=dict(color='#2196f3', width=1.5)

        ))

    if y_rep in room_df.columns:

        fig.add_trace(go.Scatter(

            x=room_df['timestamp'], y=room_df[y_rep],

            mode='lines', name='REPORTED (Telemetry)',

            line=dict(color='#f44336', width=2)

        ))



    # Highlight manipulated regions

    attacks = room_df[room_df['is_manipulated'] == True]

    if not attacks.empty and y_rep == attacks.iloc[0].get('attack_target', ''):

        fig.add_vrect(

            x0=attacks['timestamp'].min(), x1=attacks['timestamp'].max(),

            fillcolor="rgba(244,67,54,0.15)", layer="below", line_width=0,

            annotation_text="FDI ATTACK", annotation_position="top left",

            annotation=dict(font=dict(color="#f44336", size=10))

        )



    fig.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

    fig.update_layout(

        title=dict(text=title, font=dict(size=12, color='#9aa0a6')),

        yaxis_title=unit, height=280, hovermode='x unified',

        

    )

    return fig



# Telemetry charts

st.markdown(flatten_html(section_header("TELEMETRY: TRUE vs OBSERVED vs REPORTED", "📡")), unsafe_allow_html=True)



tab1, tab2, tab3, tab4 = st.tabs(["CO\u2082", "TEMPERATURE", "POWER", "OCCUPANCY & ENERGY"])



with tab1:

    st.plotly_chart(plot_true_obs_rep("CO\u2082 Concentration", 'true_co2_ppm', 'observed_co2_ppm', 'reported_co2_ppm', 'ppm'), use_container_width=True)



with tab2:

    st.plotly_chart(plot_true_obs_rep("Temperature", 'true_temperature_c', 'observed_temperature_c', 'reported_temperature_c', '\u00b0C'), use_container_width=True)



with tab3:

    st.plotly_chart(plot_true_obs_rep("Total Power", 'true_power_kw', 'observed_power_kw', 'reported_power_kw', 'kW'), use_container_width=True)



with tab4:

    c_left, c_right = st.columns(2)

    with c_left:

        fig_occ = go.Figure()

        fig_occ.add_trace(go.Scatter(

            x=room_df['timestamp'], y=room_df['occupancy'],

            mode='lines', name='Occupancy',

            line=dict(color='#2196f3', width=1.5),

            fill='tozeroy', fillcolor='rgba(33,150,243,0.1)'

        ))

        fig_occ.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

        fig_occ.update_layout(

            title=dict(text='OCCUPANCY', font=dict(size=12, color='#9aa0a6')),

            yaxis_title='People', height=250,

            

        )

        st.plotly_chart(fig_occ, use_container_width=True)



    with c_right:

        fig_e = go.Figure()

        if 'energy_cumulative_kwh' in room_df.columns:

            fig_e.add_trace(go.Scatter(

                x=room_df['timestamp'], y=room_df['energy_cumulative_kwh'],

                mode='lines', name='Cumulative Energy',

                line=dict(color='#4caf50', width=1.5),

                fill='tozeroy', fillcolor='rgba(76,175,80,0.1)'

            ))

        fig_e.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

        fig_e.update_layout(

            title=dict(text='CUMULATIVE ENERGY', font=dict(size=12, color='#9aa0a6')),

            yaxis_title='kWh', height=250,

            

        )

        st.plotly_chart(fig_e, use_container_width=True)



# Power breakdown

st.markdown(flatten_html(section_header("POWER DECOMPOSITION", "⚡")), unsafe_allow_html=True)



fig_power = go.Figure()

for col, name, color in [

    ('hvac_power_kw', 'HVAC', '#ff9800'),

    ('lighting_power_kw', 'Lighting', '#ffeb3b'),

    ('plug_power_kw', 'Plug Load', '#2196f3'),

    ('base_power_kw', 'Base Load', '#9aa0a6'),

]:

    if col in room_df.columns:

        fig_power.add_trace(go.Scatter(

            x=room_df['timestamp'], y=room_df[col],

            mode='lines', name=name, stackgroup='power',

            line=dict(width=0), fillcolor=color.replace(')', ',0.6)').replace('rgb', 'rgba') if 'rgb' in color else color,

        ))

fig_power.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

fig_power.update_layout(

    title=dict(text='POWER BY COMPONENT (STACKED)', font=dict(size=12, color='#9aa0a6')),

    yaxis_title='kW', height=280,

    

)

st.plotly_chart(fig_power, use_container_width=True)