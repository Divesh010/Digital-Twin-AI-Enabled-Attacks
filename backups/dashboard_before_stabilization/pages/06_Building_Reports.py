import textwrap
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from dashboard.data.loader import load_historical_data, get_hierarchy
from dashboard.styles import DARK_THEME_CSS, flatten_html, section_header, kpi_card, PLOTLY_DARK_TEMPLATE
st.set_page_config(page_title='Building Reports', page_icon='📑', layout='wide', initial_sidebar_state='expanded')
st.markdown(flatten_html(DARK_THEME_CSS), unsafe_allow_html=True)
st.markdown(flatten_html(section_header('BUILDING-SPECIFIC REPORTS', '📑')), unsafe_allow_html=True)
df = load_historical_data()
if df.empty:
    st.error('No data available.')
    st.stop()
df['timestamp'] = pd.to_datetime(df['timestamp'])
hierarchy = get_hierarchy(df)
buildings = df['building_id'].unique().tolist()
st.sidebar.title('Report Configuration')
selected_building = st.sidebar.selectbox('Select Building', buildings)
time_resolution = st.sidebar.selectbox('Aggregation Period', ['Hourly', 'Daily', 'Weekly', 'Monthly'])
is_vacation = st.sidebar.checkbox('Vacation Period (Weekends Only)', value=False)
bld_df = df[df['building_id'] == selected_building].copy()
if is_vacation:
    bld_df = bld_df[bld_df['timestamp'].dt.dayofweek.isin([5, 6])]
if bld_df.empty:
    st.warning('No data available for the selected filters (e.g., Vacation period may not overlap with simulated data).')
    st.stop()
if time_resolution == 'Hourly':
    bld_df['time_group'] = bld_df['timestamp'].dt.floor('h')
elif time_resolution == 'Daily':
    bld_df['time_group'] = bld_df['timestamp'].dt.floor('D')
elif time_resolution == 'Weekly':
    bld_df['time_group'] = bld_df['timestamp'].dt.to_period('W').apply(lambda r: r.start_time)
elif time_resolution == 'Monthly':
    bld_df['time_group'] = bld_df['timestamp'].dt.to_period('M').apply(lambda r: r.start_time)
agg_df = bld_df.groupby('time_group').agg({'energy_interval_kwh': 'sum', 'reported_power_kw': 'mean', 'occupancy': 'sum', 'reported_co2_ppm': 'mean', 'reported_temperature_c': 'mean', 'hvac_power_kw': 'sum', 'is_manipulated': 'sum'}).reset_index()
st.subheader(f"Report: {selected_building.replace('_', ' ').title()}")
c1, c2, c3, c4 = st.columns(4)
total_energy = agg_df['energy_interval_kwh'].sum()
avg_power = agg_df['reported_power_kw'].mean()
total_anomalies = agg_df['is_manipulated'].sum()
hvac_energy = agg_df['hvac_power_kw'].sum() * (300 / 3600.0)
total_pwr_sum = bld_df['reported_power_kw'].sum()
hvac_pwr_sum = bld_df['hvac_power_kw'].sum()
efficiency = 100 * (1 - hvac_pwr_sum / total_pwr_sum) if total_pwr_sum > 0 else 0
with c1:
    st.markdown(flatten_html(kpi_card('Total Energy', f'{total_energy:,.1f}', 'kWh', '#4caf50', '⚡')), unsafe_allow_html=True)
with c2:
    st.markdown(flatten_html(kpi_card('Avg Power', f'{avg_power:,.1f}', 'kW', '#2196f3', '🔌')), unsafe_allow_html=True)
with c3:
    st.markdown(flatten_html(kpi_card('HVAC Efficiency', f'{efficiency:,.1f}', '%', '#00bcd4', '❄️')), unsafe_allow_html=True)
with c4:
    st.markdown(flatten_html(kpi_card('Anomalies', f'{int(total_anomalies)}', 'events', '#f44336' if total_anomalies > 0 else '#4caf50', '🛡️')), unsafe_allow_html=True)
st.markdown(flatten_html('---'), unsafe_allow_html=True)
st.subheader(f'{time_resolution} Energy Consumption')
fig_energy = go.Figure()
fig_energy.add_trace(go.Bar(x=agg_df['time_group'], y=agg_df['energy_interval_kwh'], marker_color='#4caf50', name='Energy (kWh)'))
fig_energy.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
fig_energy.update_layout(yaxis_title='Energy (kWh)', height=300)
st.plotly_chart(fig_energy, width='stretch')
col_chart1, col_chart2 = st.columns(2)
with col_chart1:
    st.subheader(f'Average CO2 & Temp ({time_resolution})')
    fig_env = go.Figure()
    fig_env.add_trace(go.Scatter(x=agg_df['time_group'], y=agg_df['reported_co2_ppm'], mode='lines', name='CO2 (ppm)', line=dict(color='#00bcd4')))
    fig_env.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
    fig_env.update_layout(yaxis_title='CO2 (ppm)', height=250)
    st.plotly_chart(fig_env, width='stretch')
with col_chart2:
    st.subheader(f'Cybersecurity Alerts ({time_resolution})')
    fig_sec = go.Figure()
    fig_sec.add_trace(go.Bar(x=agg_df['time_group'], y=agg_df['is_manipulated'], marker_color='#f44336', name='Alerts'))
    fig_sec.update_layout(**PLOTLY_DARK_TEMPLATE['layout'])
    fig_sec.update_layout(yaxis_title='FDI Events', height=250)
    st.plotly_chart(fig_sec, width='stretch')
st.markdown(flatten_html('---'), unsafe_allow_html=True)
st.subheader('Data Export')
st.dataframe(agg_df, width='stretch')
csv = agg_df.to_csv(index=False).encode('utf-8')

def generate_pdf_report(building, time_res, total_n, avg_p, hvac_eff, anomalies, df):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', style='B', size=16)
    pdf.cell(0, 10, f'Smart Campus Digital Twin - Building Report', ln=True, align='C')
    pdf.set_font('Helvetica', size=12)
    pdf.cell(0, 10, f"Building: {building.replace('_', ' ').title()} | Aggregation: {time_res}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font('Helvetica', style='B', size=14)
    pdf.cell(0, 10, 'Key Performance Indicators', ln=True)
    pdf.set_font('Helvetica', size=12)
    pdf.cell(0, 8, f'Total Energy: {total_n:,.1f} kWh', ln=True)
    pdf.cell(0, 8, f'Average Power: {avg_p:,.1f} kW', ln=True)
    pdf.cell(0, 8, f'HVAC Efficiency: {hvac_eff:,.1f} %', ln=True)
    pdf.cell(0, 8, f'Total Anomalies (Cybersecurity Events): {int(anomalies)}', ln=True)
    pdf.ln(10)
    pdf.set_font('Helvetica', style='B', size=11)
    pdf.cell(0, 10, 'Aggregated Telemetry (Top 100 Records)', ln=True)
    pdf.set_font('Helvetica', style='B', size=9)
    pdf.cell(45, 8, 'Timestamp', border=1)
    pdf.cell(35, 8, 'Energy (kWh)', border=1)
    pdf.cell(35, 8, 'Avg Power (kW)', border=1)
    pdf.cell(35, 8, 'Avg CO2 (ppm)', border=1)
    pdf.cell(35, 8, 'Cyber Alerts', border=1, ln=True)
    pdf.set_font('Helvetica', size=9)
    for index, row in df.head(100).iterrows():
        tg = str(row['time_group'])[:16]
        pdf.cell(45, 8, tg, border=1)
        pdf.cell(35, 8, f"{row['energy_interval_kwh']:.2f}", border=1)
        pdf.cell(35, 8, f"{row['reported_power_kw']:.2f}", border=1)
        pdf.cell(35, 8, f"{row['reported_co2_ppm']:.0f}", border=1)
        pdf.cell(35, 8, str(int(row['is_manipulated'])), border=1, ln=True)
    return pdf.output()
pdf_bytes = generate_pdf_report(selected_building, time_resolution, total_energy, avg_power, efficiency, total_anomalies, agg_df)
c_dl1, c_dl2 = st.columns([1, 1])
with c_dl1:
    st.download_button(label='📥 Download Report (CSV)', data=csv, file_name=f'{selected_building}_{time_resolution.lower()}_report.csv', mime='text/csv', width='stretch')
with c_dl2:
    st.download_button(label='📄 Download Detailed Report (PDF)', data=bytes(pdf_bytes), file_name=f'{selected_building}_{time_resolution.lower()}_report.pdf', mime='application/pdf', width='stretch')