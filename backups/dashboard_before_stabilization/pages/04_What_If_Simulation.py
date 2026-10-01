import textwrap
import streamlit as st

import pandas as pd

import plotly.graph_objects as go

from datetime import timedelta



from dashboard.data.loader import load_app_config, load_historical_data

from dashboard.styles import (

    DARK_THEME_CSS, render_header, flatten_html, section_header, kpi_card,

    PLOTLY_DARK_TEMPLATE

)

from models.occupancy import OccupancyModel

from models.environment import CO2Model, TemperatureModel

from models.hvac import HVACController

from models.power import LightingModel, PlugLoadModel, EnergyModel



st.set_page_config(page_title="What-If Simulation", page_icon="BU", layout="wide", initial_sidebar_state="expanded")

st.markdown(flatten_html(DARK_THEME_CSS), unsafe_allow_html=True)



config = load_app_config()

df_hist = load_historical_data()



mqtt_connected = (

    st.session_state.get('mqtt_client') is not None

    and st.session_state.mqtt_client.is_connected

)

record_count = len(df_hist) if not df_hist.empty else 0

last_ts = df_hist['timestamp'].max().strftime("%Y-%m-%d %H:%M") if not df_hist.empty else "--"

render_header(mqtt_connected=mqtt_connected, record_count=record_count, last_update=last_ts)



st.markdown(flatten_html(section_header("WHAT-IF SCENARIO SIMULATOR", "🧪")), unsafe_allow_html=True)



st.markdown(flatten_html("""

<div style="background: #151c25; border: 1px solid #2a3441; border-radius: 2px; padding: 12px 16px; margin-bottom: 12px;">

    <div style="font-size: 11px; color: #9aa0a6; line-height: 1.6;">

        <b style="color: #e8eaed;">Interactive Digital Twin Scenario Analysis.</b>

        Explore physical outcomes by adjusting occupancy and HVAC parameters.

        Uses the validated Phase 5 physics models initialized from the selected room's configuration.

        The baseline dataset is never modified.

    </div>

</div>

"""), unsafe_allow_html=True)



# Hierarchy selection from config

st.sidebar.markdown(flatten_html("""

<div style="font-size: 10px; color: #00bcd4; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; font-weight: 700;">

    Scenario Target

</div>

"""), unsafe_allow_html=True)



st.sidebar.markdown(flatten_html(f"**Campus:** {config.campus.id.replace('_',' ').title()}"), unsafe_allow_html=True)

selected_building_id = st.sidebar.selectbox("Building", [b.id for b in config.campus.buildings])

selected_building = next(b for b in config.campus.buildings if b.id == selected_building_id)



selected_floor_id = st.sidebar.selectbox("Floor", [f.id for f in selected_building.floors])

selected_floor = next(f for f in selected_building.floors if f.id == selected_floor_id)



selected_room_id = st.sidebar.selectbox("Room", [r.id for r in selected_floor.rooms])

room_config = next(r for r in selected_floor.rooms if r.id == selected_room_id)



# Current state display

bld_name = selected_building_id.replace("_", " ").title()

flr_name = selected_floor_id.replace("_", " ").title()



st.markdown(flatten_html(f"""

<div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">

    <div style="background: #1a222d; border: 1px solid #2a3441; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #9aa0a6;">BUILDING</span> <span style="color: #e8eaed; font-weight: 600;">{bld_name}</span>

    </div>

    <div style="color: #2a3441; font-size: 14px;">▸</div>

    <div style="background: #1a222d; border: 1px solid #2a3441; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #9aa0a6;">FLOOR</span> <span style="color: #e8eaed; font-weight: 600;">{flr_name}</span>

    </div>

    <div style="color: #2a3441; font-size: 14px;">▸</div>

    <div style="background: #00bcd4; border-radius: 2px; padding: 4px 10px; font-size: 10px;">

        <span style="color: #0a0e14; font-weight: 700;">ROOM {selected_room_id}</span>

    </div>

</div>

"""), unsafe_allow_html=True)



# Room config display

st.markdown(flatten_html(section_header("CURRENT ROOM CONFIGURATION", "⚙️")), unsafe_allow_html=True)



cfg_cols = st.columns(5)

with cfg_cols[0]:

    st.markdown(flatten_html(kpi_card("Capacity", f"{room_config.capacity}", "persons", "#2196f3")), unsafe_allow_html=True)

with cfg_cols[1]:

    st.markdown(flatten_html(kpi_card("Volume", f"{room_config.volume_m3:.0f}", "m\u00b3", "#00bcd4")), unsafe_allow_html=True)

with cfg_cols[2]:

    st.markdown(flatten_html(kpi_card("HVAC Capacity", f"{room_config.hvac.cooling_capacity_kw:.0f}", "kW", "#ff9800")), unsafe_allow_html=True)

with cfg_cols[3]:

    st.markdown(flatten_html(kpi_card("COP", f"{room_config.hvac.cop:.1f}", "", "#009688")), unsafe_allow_html=True)

with cfg_cols[4]:

    st.markdown(flatten_html(kpi_card("Setpoint", f"{room_config.hvac.setpoint_c:.1f}", "\u00b0C", "#00bcd4")), unsafe_allow_html=True)



# Scenario parameters

st.markdown(flatten_html(section_header("SCENARIO PARAMETERS", "🎛️")), unsafe_allow_html=True)



c1, c2 = st.columns(2)

with c1:

    occ_multiplier = st.slider("Occupancy Multiplier", 0.0, 2.0, 1.0, 0.1,

                                help="Scale occupancy schedule (1.0 = baseline)")

with c2:

    hvac_setpoint = st.slider("HVAC Setpoint (\u00b0C)", 18.0, 30.0, float(room_config.hvac.setpoint_c), 0.5,

                               help="Override thermostat setpoint")



# Run simulation

if st.button("RUN SCENARIO", type="primary", use_container_width=True):

    with st.spinner("Running Phase 5 physics simulation..."):

        schedule = next(s for s in config.schedules if s.id == room_config.schedule_id)

        scaled_profile = {k: min(1.0, v * occ_multiplier) for k, v in schedule.profile.items()}

        if not scaled_profile:

            scaled_profile = {"00:00": 0.0}



        occ_model = OccupancyModel(capacity=room_config.capacity, schedule_profile=scaled_profile, seed=42)

        co2_model = CO2Model(

            volume_m3=room_config.volume_m3,

            generation_rate_m3_s_person=room_config.co2.generation_rate_m3_s_person,

            ventilation_rate_m3_s=room_config.co2.ventilation_rate_m3_s,

            initial_co2_ppm=config.physics.outdoor_co2_ppm

        )

        temp_model = TemperatureModel(

            thermal_mass_j_c=room_config.temperature.thermal_mass_j_c,

            thermal_resistance_c_w=room_config.temperature.thermal_resistance_c_w,

            heat_per_person_w=room_config.temperature.heat_per_person_w,

            initial_temp_c=room_config.hvac.setpoint_c

        )

        hvac = HVACController(

            cooling_capacity_kw=room_config.hvac.cooling_capacity_kw,

            cop=room_config.hvac.cop,

            setpoint_c=hvac_setpoint,

            upper_deadband_c=room_config.hvac.upper_deadband_c,

            lower_deadband_c=room_config.hvac.lower_deadband_c,

            min_on_time_minutes=room_config.hvac.min_on_time_minutes,

            min_off_time_minutes=room_config.hvac.min_off_time_minutes,

            stage_fractions=room_config.hvac.stage_fractions

        )

        light_model = LightingModel(capacity_kw=room_config.power.lighting_capacity_kw)

        plug_model = PlugLoadModel(plug_load_per_person_kw=room_config.power.plug_load_per_person_kw, seed=42)

        energy_model = EnergyModel()



        dt_seconds = config.simulation.dt_seconds

        current_time = config.simulation.start_datetime

        end_time = current_time + timedelta(hours=24)



        records = []

        t_obs = room_config.hvac.setpoint_c

        outdoor_temp = config.physics.outdoor_temperature_c



        while current_time < end_time:

            occ = occ_model.step(current_time)

            hvac_st, hvac_p_kw, hvac_th_w = hvac.step(dt_seconds, t_obs)

            p_light = light_model.step(occ)

            p_plug = plug_model.step(occ)

            co2 = co2_model.step(dt_seconds, occ, config.physics.outdoor_co2_ppm)

            t_true = temp_model.step(dt_seconds, occ, p_light * 1000, p_plug * 1000, hvac_th_w, outdoor_temp)

            t_obs = t_true

            p_tot, e_int, e_cum = energy_model.step(dt_seconds, room_config.power.base_load_kw, p_light, p_plug, hvac_p_kw)



            records.append({

                'timestamp': current_time, 'occupancy': occ, 'co2_ppm': co2,

                'temperature_c': t_true, 'power_kw': p_tot,

                'hvac_power_kw': hvac_p_kw, 'energy_kwh': e_cum

            })

            current_time += timedelta(seconds=dt_seconds)



        df_sim = pd.DataFrame(records)



    # Results

    st.markdown(flatten_html(section_header("SCENARIO RESULTS", "📊")), unsafe_allow_html=True)



    total_energy = df_sim['energy_kwh'].iloc[-1]

    peak_power = df_sim['power_kw'].max()

    avg_temp = df_sim['temperature_c'].mean()

    max_co2 = df_sim['co2_ppm'].max()

    avg_occ = df_sim['occupancy'].mean()

    CARBON_FACTOR = 0.82

    total_carbon = total_energy * CARBON_FACTOR



    rc1, rc2, rc3, rc4, rc5, rc6 = st.columns(6)

    with rc1:

        st.markdown(flatten_html(kpi_card("Total Energy", f"{total_energy:,.1f}", "kWh", "#4caf50")), unsafe_allow_html=True)

    with rc2:

        st.markdown(flatten_html(kpi_card("Peak Power", f"{peak_power:,.2f}", "kW", "#ff9800")), unsafe_allow_html=True)

    with rc3:

        st.markdown(flatten_html(kpi_card("Avg Temp", f"{avg_temp:,.1f}", "\u00b0C", "#00bcd4")), unsafe_allow_html=True)

    with rc4:

        st.markdown(flatten_html(kpi_card("Max CO\u2082", f"{max_co2:,.0f}", "ppm", "#009688")), unsafe_allow_html=True)

    with rc5:

        st.markdown(flatten_html(kpi_card("CO\u2082 Emissions", f"{total_carbon:,.1f}", "kg CO\u2082", "#009688")), unsafe_allow_html=True)

    with rc6:

        st.markdown(flatten_html(kpi_card("Timesteps", f"{len(df_sim)}", "@ 5 min", "#2196f3")), unsafe_allow_html=True)



    # Charts

    tab1, tab2, tab3, tab4 = st.tabs(["TEMPERATURE", "POWER", "CO\u2082", "OCCUPANCY"])



    with tab1:

        fig_t = go.Figure()

        fig_t.add_trace(go.Scatter(

            x=df_sim['timestamp'], y=df_sim['temperature_c'],

            mode='lines', name='Scenario Temperature',

            line=dict(color='#00bcd4', width=2)

        ))

        fig_t.add_hline(y=hvac_setpoint, line_dash="dash", line_color="#ff9800",

                        annotation_text=f"Setpoint: {hvac_setpoint}\u00b0C")

        fig_t.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

        fig_t.update_layout(

            title=dict(text='PREDICTED TEMPERATURE', font=dict(size=12, color='#9aa0a6')),

            yaxis_title='\u00b0C', height=300

        )

        st.plotly_chart(fig_t, use_container_width=True)



    with tab2:

        fig_p = go.Figure()

        fig_p.add_trace(go.Scatter(

            x=df_sim['timestamp'], y=df_sim['power_kw'],

            mode='lines', name='Total Power',

            line=dict(color='#4caf50', width=2),

            fill='tozeroy', fillcolor='rgba(76,175,80,0.1)'

        ))

        fig_p.add_trace(go.Scatter(

            x=df_sim['timestamp'], y=df_sim['hvac_power_kw'],

            mode='lines', name='HVAC Power',

            line=dict(color='#ff9800', width=1.5, dash='dash')

        ))

        fig_p.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

        fig_p.update_layout(

            title=dict(text='PREDICTED POWER CONSUMPTION', font=dict(size=12, color='#9aa0a6')),

            yaxis_title='kW', height=300

        )

        st.plotly_chart(fig_p, use_container_width=True)



    with tab3:

        fig_c = go.Figure()

        fig_c.add_trace(go.Scatter(

            x=df_sim['timestamp'], y=df_sim['co2_ppm'],

            mode='lines', name='CO\u2082',

            line=dict(color='#009688', width=2),

            fill='tozeroy', fillcolor='rgba(0,150,136,0.1)'

        ))

        fig_c.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

        fig_c.update_layout(

            title=dict(text='PREDICTED CO\u2082 CONCENTRATION', font=dict(size=12, color='#9aa0a6')),

            yaxis_title='ppm', height=300

        )

        st.plotly_chart(fig_c, use_container_width=True)



    with tab4:

        fig_o = go.Figure()

        fig_o.add_trace(go.Scatter(

            x=df_sim['timestamp'], y=df_sim['occupancy'],

            mode='lines', name='Occupancy',

            line=dict(color='#2196f3', width=1.5),

            fill='tozeroy', fillcolor='rgba(33,150,243,0.1)'

        ))

        fig_o.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])

        fig_o.update_layout(

            title=dict(text='PREDICTED OCCUPANCY', font=dict(size=12, color='#9aa0a6')),

            yaxis_title='People', height=300

        )

        st.plotly_chart(fig_o, use_container_width=True)