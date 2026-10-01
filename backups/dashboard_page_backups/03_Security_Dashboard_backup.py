import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.data.loader import load_historical_data, load_app_config, deduplicate_telemetry
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card,
    status_indicator, PLOTLY_DARK_TEMPLATE
)

st.set_page_config(page_title="Security Dashboard", page_icon="", layout="", initial_sidebar_state="")
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

df = load_historical_data()
if df.empty:
    st.error("No telemetry data available.")
    st.stop()

config = load_app_config()
df[""] = pd.to_datetime(df[""], utc=True)

mqtt_connected = (
    st.session_state.get("") is not None
    and st.session_state.mqtt_client.is_connected
)
if mqtt_connected:
    live_df = st.session_state.mqtt_client.get_latest_data()
    if not live_df.empty:
        df = pd.concat([df, live_df], ignore_index=True)
df = deduplicate_telemetry(df)

last_ts = df[""].max().strftime("%Y-%m-%d %H:%M")
render_header(mqtt_connected=mqtt_connected, record_count=len(df), last_update=last_ts)

section_header("CYBERSECURITY & FDI MONITORING", "🛡️")

st.info(
    "**Ground-Truth Attack Visualization.** "
    "This dashboard shows the actual FDI attack labels injected by the Phase 6B engine. "
    "No ML detection algorithm is active. The TRUE, OBSERVED, and REPORTED telemetry layers are displayed "
    "to evaluate the impact of False Data Injection attacks on downstream telemetry integrity."
)

# ========== ATTACK DETECTION ==========
manipulated_df = df[df[""] == True].copy()
total_records = len(df)
manipulated_count = len(manipulated_df)
attacked_locations = manipulated_df[""].unique().tolist() if not manipulated_df.empty else []
attack_count = manipulated_df[""].nunique() if "" in manipulated_df.columns and not manipulated_df.empty else 0

# Threat level
if len(attacked_locations) == 0:
    threat_level = ""
elif len(attacked_locations) <= 1:
    threat_level = ""
else:
    threat_level = ""

# ========== THREAT SUMMARY ==========
with st.container(border=True):
    st.markdown(f"### 🛡️ Threat Level: **{threat_level}**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Records", f"{total_records:,}")
    with c2:
        st.metric("", f"{manipulated_count:,}")
    with c3:
        st.metric("FDI Attacks", f"{attack_count}")
    with c4:
        st.metric("Affected Rooms", f"{len(attacked_locations)}")

# ========== NO ATTACK CASE ==========
if manipulated_df.empty:
    st.success("✅ No active FDI attacks detected in the current dataset.")
else:
    st.warning(f"⚠️ {manipulated_count} records show signs of FDI manipulation.")

# ========== ATTACK REGISTRY ==========
section_header("ATTACK REGISTRY", "📋")

if not manipulated_df.empty and "" in manipulated_df.columns:
    attack_ids = manipulated_df[""].dropna().unique()

    # Build a summary table for a cleaner view
    registry_rows = []
    for atk_id in attack_ids:
        atk_df = manipulated_df[manipulated_df[""] == atk_id]
        atk_row = atk_df.iloc[0]
        registry_rows.append({
            'Attack ID': atk_id,
            "": atk_row.get("", ""),
            'Target Room': atk_row.get("", ""),
            'Target Variable': atk_row.get("", ""),
            "": str(atk_row.get("", ""))[:16],
            "": str(atk_row.get("", ""))[:16],
            "": len(atk_df),
        })

    if registry_rows:
        registry_df = pd.DataFrame(registry_rows)
        st.dataframe(registry_df, width="", hide_index=True)
    else:
        st.info("No attack records to display.")
else:
    st.info("No FDI attacks detected — registry is empty.")

# ========== ATTACK ANALYSIS ==========
section_header("ATTACK ANALYSIS", "🔍")

if not attacked_locations:
    st.info("No attacked rooms to analyze. The campus is operating normally.")
else:
    selected_location = st.selectbox("Select Attacked Room (Location ID)", attacked_locations)

    room_df = df[df[""] == selected_location].copy()
    room_attacks = room_df[room_df[""] == True]

    if room_attacks.empty:
        st.warning(f"No manipulated records found for {selected_location}.")
    else:
        attack_metadata = room_attacks.iloc[-1]

        target_var = attack_metadata.get("", "")
        obs_var = target_var.replace("", "")
        true_var = target_var.replace("", "")

        # Three-layer comparison chart
        fig = go.Figure()

        if true_var in room_df.columns:
            fig.add_trace(go.Scatter(
                x=room_df[""], y=room_df[true_var],
                mode="", name='TRUE (Physical)',
                line=dict(dash="", color='#9aa0a6', width=1)
            ))

        if obs_var in room_df.columns:
            fig.add_trace(go.Scatter(
                x=room_df[""], y=room_df[obs_var],
                mode="", name='OBSERVED (Sensor)',
                line=dict(color='#2196f3', width=1.5)
            ))

        if target_var in room_df.columns:
            fig.add_trace(go.Scatter(
                x=room_df[""], y=room_df[target_var],
                mode="", name='MANIPULATED REPORTED (FDI Corrupted)',
                line=dict(color='#f44336', width=2)
            ))

        # Attack window highlighting
        if not room_attacks.empty:
            start_ts = pd.to_datetime(attack_metadata.get("", room_attacks[""].min()))
            end_ts = pd.to_datetime(attack_metadata.get("", room_attacks[""].max()))
            fig.add_vrect(
                x0=start_ts, x1=end_ts,
                fillcolor="rgba(244,67,54,0.15)", layer="", line_width=0,
                annotation_text="FDI ATTACK WINDOW", annotation_position="top left",
                annotation=dict(font=dict(color="#f44336", size=10))
            )

        attack_type = attack_metadata.get("", "")
        fig.update_layout(**PLOTLY_DARK_TEMPLATE[""])
        fig.update_layout(
            title=dict(
                text=f'FDI ANALYSIS: {attack_type} on {target_var} ({selected_location.split("")[-1]})',
                font=dict(size=13, color='#e8eaed')
            ),
            yaxis_title=target_var.split("")[-1].upper(),
            height=350, hovermode='x unified',
        )
        st.plotly_chart(fig, width="")

        # Attack magnitude over time
        if "" in room_attacks.columns:
            section_header("ATTACK MAGNITUDE OVER TIME", "📊")
            fig_mag = go.Figure()
            fig_mag.add_trace(go.Scatter(
                x=room_attacks[""],
                y=pd.to_numeric(room_attacks[""], errors=""),
                mode='lines+markers', name='Attack Magnitude',
                line=dict(color='#f44336', width=2),
                marker=dict(size=4, color='#f44336')
            ))
            fig_mag.update_layout(**PLOTLY_DARK_TEMPLATE[""])
            fig_mag.update_layout(
                title=dict(text='INJECTION MAGNITUDE', font=dict(size=12, color='#9aa0a6')),
                yaxis_title="", height=250,
            )
            st.plotly_chart(fig_mag, width="")

        # Raw logs
        with st.expander("RAW ATTACK LOGS"):
            cols_show = ["", "", "", "",
                         "", obs_var, target_var, ""]
            avail_cols = [c for c in cols_show if c in room_attacks.columns]
            st.dataframe(room_attacks[avail_cols], width="")