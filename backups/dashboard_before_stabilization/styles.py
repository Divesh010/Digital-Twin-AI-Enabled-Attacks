import streamlit as st
import re
"""
Industrial Digital Twin Dashboard Styles
Dark operational dashboard theme inspired by Nuclear AMRC/Sheffield DT platform.
"""

DARK_THEME_CSS = """
<style>
/* ========== GLOBAL RESET & DARK THEME ========== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Hide Streamlit default elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
div[data-testid="stToolbar"] {display: none;}
div[data-testid="stDecoration"] {display: none;}

/* Root variables */
:root {
    --bg-primary: #0a0e14;
    --bg-secondary: #111820;
    --bg-panel: #151c25;
    --bg-card: #1a222d;
    --accent-cyan: #00bcd4;
    --accent-teal: #009688;
    --accent-green: #4caf50;
    --accent-blue: #2196f3;
    --accent-orange: #ff9800;
    --accent-red: #f44336;
    --accent-yellow: #ffeb3b;
    --text-primary: #e8eaed;
    --text-secondary: #9aa0a6;
    --text-dim: #5f6368;
    --border-color: #2a3441;
    --kpi-value: #4caf50;
}

/* Global background */
.stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Main content area */
.main .block-container {
    padding-top: 0 !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-color) !important;
    width: 260px !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: var(--text-primary) !important;
    font-size: 0.85rem !important;
}
section[data-testid="stSidebar"] label {
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* Selectbox styling */
div[data-baseweb="select"] {
    background-color: var(--bg-card) !important;
    border-color: var(--border-color) !important;
}
div[data-baseweb="select"] > div {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
}

/* Slider styling */
div[data-testid="stSlider"] label {
    color: var(--text-secondary) !important;
}

/* Button styling */
.stButton > button {
    background-color: var(--accent-cyan) !important;
    color: var(--bg-primary) !important;
    border: none !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    border-radius: 2px !important;
    padding: 0.5rem 2rem !important;
}
.stButton > button:hover {
    background-color: var(--accent-teal) !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px !important;
    background-color: var(--bg-secondary) !important;
    border-bottom: 2px solid var(--border-color) !important;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    color: var(--text-secondary) !important;
    border: none !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
    padding: 0.75rem 1.5rem !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent-cyan) !important;
    border-bottom: 2px solid var(--accent-cyan) !important;
}

/* Metrics */
div[data-testid="stMetric"] {
    background-color: var(--bg-panel) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 4px !important;
    padding: 1rem !important;
}
div[data-testid="stMetric"] label {
    color: var(--text-secondary) !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: var(--kpi-value) !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

/* Dataframe */
div[data-testid="stDataFrame"] {
    background-color: var(--bg-panel) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 4px !important;
}

/* Expander */
div[data-testid="stExpander"] {
    background-color: var(--bg-panel) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 4px !important;
}
div[data-testid="stExpander"] summary {
    color: var(--text-primary) !important;
}

/* Markdown headers */
.stMarkdown h1 { color: var(--text-primary) !important; font-weight: 700 !important; }
.stMarkdown h2 { color: var(--accent-cyan) !important; font-weight: 600 !important; }
.stMarkdown h3 { color: var(--text-primary) !important; font-weight: 600 !important; }
.stMarkdown p { color: var(--text-secondary) !important; }

/* Plotly chart backgrounds */
.js-plotly-plot .plotly .main-svg {
    background-color: transparent !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-cyan); }

/* Alert boxes */
div[data-testid="stAlert"] {
    background-color: var(--bg-panel) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
}
</style>
"""


import textwrap

def flatten_html(html_str):
    return re.sub(r'^\s+', '', html_str, flags=re.MULTILINE).replace('\n', '')


def render_header(mqtt_connected=False, record_count=0, last_update="--"):
    mqtt_status = "🟢 ONLINE" if mqtt_connected else "🔴 OFFLINE"
    mode = "LIVE" if mqtt_connected else "HISTORICAL"
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    
    with col1:
        st.markdown("**BU | Bennett University**")
        st.caption("Smart Campus Digital Twin")
        
    with col2:
        st.markdown("<h4 style='text-align: center; color: #00bcd4; margin: 0;'>Energy, Carbon & Cybersecurity Monitoring Platform</h4>", unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"**System:** 🟢 ONLINE | **MQTT:** {mqtt_status}")
        st.caption(f"**Mode:** {mode} | **Records:** {record_count:,}")
    st.markdown("---")



def section_header(title, icon=""):
    """Create a cyan section header bar like the reference."""
    html = f"""
    <div style="
        background: linear-gradient(90deg, #00bcd4 0%, #009688 100%);
        padding: 8px 16px;
        margin: 1rem 0 0.75rem 0;
        border-radius: 2px;
        display: flex;
        align-items: center;
        gap: 8px;
    ">
        <span style="font-size: 14px;">{icon}</span>
        <span style="
            color: white;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
        ">{title}</span>
    </div>
    """
    return flatten_html(html)


def kpi_card(label, value, unit="", color="#4caf50", icon=""):
    """Create an industrial-style KPI card."""
    html = f"""
    <div style="
        background: #151c25;
        border: 1px solid #2a3441;
        border-left: 3px solid {color};
        border-radius: 2px;
        padding: 12px 16px;
        text-align: center;
        min-height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    ">
        <div style="font-size: 9px; color: #9aa0a6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">
            {icon} {label}
        </div>
        <div style="font-size: 24px; font-weight: 700; color: {color}; line-height: 1.1;">
            {value}
        </div>
        <div style="font-size: 10px; color: #5f6368; margin-top: 2px;">{unit}</div>
    </div>
    """
    return flatten_html(html)


def status_indicator(label, status, color="#4caf50"):
    """Create a small status indicator."""
    html = f"""
    <div style="display: flex; align-items: center; gap: 6px; margin: 2px 0;">
        <span style="display:inline-block;width:8px;height:8px;background:{color};border-radius:50%;"></span>
        <span style="font-size: 11px; color: #9aa0a6;">{label}:</span>
        <span style="font-size: 11px; color: {color}; font-weight: 600;">{status}</span>
    </div>
    """
    return flatten_html(html)


def hierarchy_badge(level, name, active=False):
    """Create a hierarchy navigation badge."""
    bg = "#00bcd4" if active else "#1a222d"
    text_color = "#0a0e14" if active else "#e8eaed"
    border = "#00bcd4" if active else "#2a3441"
    html = f"""
    <div style="
        background: {bg};
        border: 1px solid {border};
        border-radius: 2px;
        padding: 4px 10px;
        display: inline-block;
        margin: 2px;
    ">
        <span style="font-size: 8px; color: {'#0a0e14' if active else '#9aa0a6'}; text-transform: uppercase; letter-spacing: 1px;">{level}</span><br/>
        <span style="font-size: 11px; color: {text_color}; font-weight: 600;">{name}</span>
    </div>
    """
    return flatten_html(html)


PLOTLY_DARK_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#111820',
        font=dict(color='#9aa0a6', family='Inter, sans-serif', size=11),
        xaxis=dict(
            gridcolor='#1a222d',
            linecolor='#2a3441',
            zerolinecolor='#2a3441',
        ),
        yaxis=dict(
            gridcolor='#1a222d',
            linecolor='#2a3441',
            zerolinecolor='#2a3441',
        ),
        margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='#9aa0a6', size=10),
        ),
        colorway=['#00bcd4', '#4caf50', '#ff9800', '#f44336', '#2196f3', '#9c27b0', '#ffeb3b'],
    )
)
