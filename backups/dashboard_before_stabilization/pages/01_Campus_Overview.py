import textwrap
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dashboard.data.loader import load_historical_data, get_hierarchy, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, flatten_html, section_header, kpi_card,
    status_indicator, hierarchy_badge, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Campus Overview", page_icon="BU", layout="wide", initial_sidebar_state="expanded")
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

st.markdown(flatten_html(section_header("CAMPUS OVERVIEW", "📊")), unsafe_allow_html=True)

hierarchy = get_hierarchy(df)
buildings = df['building_id'].unique().tolist()
rooms = df['room_id'].unique().tolist()

latest_time = df['timestamp'].max()
latest_df = df[df['timestamp'] == latest_time]
total_energy_kwh = df['energy_interval_kwh'].sum()
current_power_kw = latest_df['reported_power_kw'].sum()
avg_co2 = latest_df['reported_co2_ppm'].mean()
avg_temp = latest_df['reported_temperature_c'].mean()
total_occ = int(latest_df['occupancy'].sum())
num_rooms = len(latest_df['location_id'].unique())
peak_power = df.groupby('timestamp')['reported_power_kw'].sum().max()
hvac_energy = df['hvac_power_kw'].sum() * (config.simulation.dt_seconds / 3600.0)
manipulated_df = df[df['is_manipulated'] == True]
rooms_under_attack = len(manipulated_df['location_id'].unique())
attack_count = manipulated_df['attack_id'].nunique() if 'attack_id' in manipulated_df.columns else 0

CARBON_FACTOR = 0.82
total_carbon_kg = total_energy_kwh * CARBON_FACTOR
daily_energy = total_energy_kwh / 7.0
daily_carbon = total_carbon_kg / 7.0
carbon_intensity = total_carbon_kg / total_energy_kwh if total_energy_kwh > 0 else 0

# ========== TOP ROW: Infrastructure & Core KPIs ==========
top_col1, top_col2, top_col3 = st.columns([1, 1.5, 1.5])

with top_col1:
    st.markdown(flatten_html("""
    <div style="background: #151c25; border: 1px solid #2a3441; border-radius: 2px; padding: 12px; height: 100%;">
        <div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Facility Profile</div>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="
                width: 60px; height: 60px;
                background: linear-gradient(135deg, #1a222d 0%, #2a3441 100%);
                border: 1px solid #00bcd4; border-radius: 4px;
                display: flex; align-items: center; justify-content: center;
                font-size: 24px;
            ">🏛️</div>
            <div>
                <div style="font-size: 13px; color: #e8eaed; font-weight: 600; text-transform: uppercase;">Bennett University</div>
                <div style="font-size: 11px; color: #00bcd4;">Main Campus</div>
            </div>
        </div>
        <div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Hierarchy</div>
        <div style="display: flex; gap: 4px; font-size: 11px; color: #e8eaed; align-items: center;">
            <span style="color: #00bcd4;">UNIV</span> ➔ <span style="color: #00bcd4;">CAMP</span> ➔ <span style="color: #00bcd4;">BLDG</span> ➔ <span style="color: #00bcd4;">FLR</span> ➔ <span style="color: #00bcd4;">RM</span>
        </div>
    </div>
    """), unsafe_allow_html=True)

with top_col2:
    st.markdown(flatten_html("""<div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Energy Information</div>"""), unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(flatten_html(kpi_card("Current Power", f"{current_power_kw:,.2f}", "kW", "#2196f3", "🔌")), unsafe_allow_html=True)
    with c2: st.markdown(flatten_html(kpi_card("Daily Energy", f"{daily_energy:,.1f}", "kWh/day", "#4caf50", "⚡")), unsafe_allow_html=True)
    with c3: st.markdown(flatten_html(kpi_card("Peak Power", f"{peak_power:,.2f}", "kW", "#ff9800", "📈")), unsafe_allow_html=True)

with top_col3:
    st.markdown(flatten_html("""<div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Carbon Information</div>"""), unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(flatten_html(kpi_card("Total CO\u2082", f"{total_carbon_kg:,.1f}", "kg", "#009688", "🌿")), unsafe_allow_html=True)
    with c2: st.markdown(flatten_html(kpi_card("Daily CO\u2082", f"{daily_carbon:,.1f}", "kg/day", "#009688", "📅")), unsafe_allow_html=True)
    with c3: st.markdown(flatten_html(kpi_card("Intensity", f"{carbon_intensity:,.2f}", "kg/kWh", "#009688", "🎯")), unsafe_allow_html=True)

# ========== MIDDLE ROWS: Full Width Charts ==========
st.markdown(flatten_html(section_header("LIVE ENERGY CONSUMPTION", "⚡")), unsafe_allow_html=True)
agg_power = df.groupby('timestamp')['reported_power_kw'].sum().reset_index()
fig_energy = go.Figure()
fig_energy.add_trace(go.Scatter(
    x=agg_power['timestamp'], y=agg_power['reported_power_kw'],
    mode='lines', name='Total Power',
    line=dict(color='#4caf50', width=1.5),
    fill='tozeroy', fillcolor='rgba(76,175,80,0.1)'
))
fig_energy.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
fig_energy.update_layout(
    yaxis_title='Power (kW)',
    height=200, margin=dict(l=40, r=20, t=10, b=20)
)
st.plotly_chart(fig_energy, use_container_width=True)


st.markdown(flatten_html(section_header("CARBON EMISSIONS TREND", "🌿")), unsafe_allow_html=True)
daily_df = df.copy()
daily_df['date'] = daily_df['timestamp'].dt.date
daily_carbon_series = daily_df.groupby('date')['energy_interval_kwh'].sum() * CARBON_FACTOR
fig_carbon = go.Figure()
fig_carbon.add_trace(go.Bar(
    x=daily_carbon_series.index, y=daily_carbon_series.values,
    marker_color='#009688', name='Daily CO\u2082'
))
fig_carbon.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
fig_carbon.update_layout(
    yaxis_title='kg CO\u2082',
    height=200, margin=dict(l=40, r=20, t=10, b=20)
)
st.plotly_chart(fig_carbon, use_container_width=True)

# ========== BOTTOM ROW: 3-Column Breakdown ==========
st.markdown(flatten_html(section_header("FACILITY BREAKDOWN & SECURITY", "🏢")), unsafe_allow_html=True)

bot_col1, bot_col2, bot_col3 = st.columns(3)

with bot_col1:
    bld_html = """
    <div style="background: #151c25; border: 1px solid #2a3441; border-radius: 2px; padding: 12px;">
        <div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Buildings</div>
    """
    for bld in buildings:
        bld_df = df[df['building_id'] == bld]
        bld_energy = bld_df['energy_interval_kwh'].sum()
        bld_rooms = bld_df['room_id'].nunique()
        bld_name = bld.replace("_", " ").title()
        bld_html += f"""
        <div style="background: #1a222d; border: 1px solid #2a3441; border-left: 2px solid #00bcd4; padding: 6px 10px; margin: 4px 0;">
            <div style="font-size: 11px; color: #e8eaed; font-weight: 600;">{bld_name}</div>
            <div style="font-size: 10px; color: #9aa0a6;">Rooms: {bld_rooms} | Energy: {bld_energy:,.1f} kWh</div>
        </div>
        """
    bld_html += "</div>"
    st.markdown(flatten_html(bld_html), unsafe_allow_html=True)

with bot_col2:
    r_html = """
    <div style="background: #151c25; border: 1px solid #2a3441; border-radius: 2px; padding: 12px;">
        <div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Room Status (Sample)</div>
    """
    for r in rooms[:6]:  # Limit to 6 rooms to keep density balanced
        r_df = df[df['room_id'] == r]
        if r_df.empty: continue
        r_latest = r_df.iloc[-1]
        is_manipulated = r_latest.get('is_manipulated', False)
        status_color = "#f44336" if is_manipulated else "#4caf50"
        r_html += f"""
        <div style="background: #1a222d; border: 1px solid #2a3441; border-left: 2px solid {status_color}; padding: 6px 10px; margin: 4px 0; display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 11px; color: #e8eaed; font-weight: 600;">Room {r}</div>
            <div style="font-size: 10px; color: #9aa0a6;">{r_latest.get('reported_temperature_c',0):.1f}\u00b0C | {r_latest.get('reported_co2_ppm',0):.0f} ppm</div>
        </div>
        """
    r_html += "</div>"
    st.markdown(flatten_html(r_html), unsafe_allow_html=True)

with bot_col3:
    if rooms_under_attack > 0:
        sec_status = "ATTACK DETECTED"
        sec_color = "#f44336"
        sec_bg = "rgba(244,67,54,0.1)"
    else:
        sec_status = "NORMAL"
        sec_color = "#4caf50"
        sec_bg = "rgba(76,175,80,0.1)"

    st.markdown(flatten_html(f"""
    <div style="background: {sec_bg}; border: 1px solid {sec_color}; border-radius: 2px; padding: 12px; margin-bottom: 12px;">
        <div style="font-size: 10px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Cybersecurity Status</div>
        <div style="font-size: 14px; color: {sec_color}; font-weight: 700; margin-bottom: 8px;">{sec_status}</div>
        {status_indicator("System Integrity", sec_status, sec_color)}
        {status_indicator("Active Attacks", str(rooms_under_attack), sec_color)}
        {status_indicator("Total FDI Events", str(attack_count), "#ff9800" if attack_count > 0 else "#4caf50")}
    </div>
    """), unsafe_allow_html=True)
    
    efficiency_score = 100 * (1 - (hvac_energy / total_energy_kwh)) if total_energy_kwh > 0 else 0
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=efficiency_score,
        title={'text': "Operational Efficiency", 'font': {'size': 12, 'color': '#9aa0a6'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#2a3441"},
            'bar': {'color': "#00bcd4"},
            'bgcolor': "#1a222d",
            'borderwidth': 1,
            'bordercolor': "#2a3441",
            'steps': [
                {'range': [0, 50], 'color': "rgba(244,67,54,0.3)"},
                {'range': [50, 75], 'color': "rgba(255,152,0,0.3)"},
                {'range': [75, 100], 'color': "rgba(76,175,80,0.3)"}
            ]
        }
    ))
    fig_gauge.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
    fig_gauge.update_layout(height=180, margin=dict(l=20, r=20, t=30, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)