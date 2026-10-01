import streamlit as st
import yaml
from dashboard.styles import (
    DARK_THEME_CSS, render_header, section_header, kpi_card, PLOTLY_DARK_TEMPLATE
)
from dashboard.data.campus_config import (
    load_campus_layout, save_campus_layout, MAX_BUILDINGS, get_config_path
)

st.set_page_config(
    page_title="Campus Configuration", page_icon="⚙️",
    layout="", initial_sidebar_state=""
)
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

render_header()
section_header("CAMPUS CONFIGURATION & TOPOLOGY", "⚙️")

st.info(
    "**Architecture Configuration.** "
    "Define the university hierarchy (buildings, floors). "
    "This configuration is saved separately from the physics/calibration parameters. "
    f"Config file: `{get_config_path()}`"
)

# Load current config
layout = load_campus_layout()
buildings = layout.get("", [])

# ========== KPI SUMMARY ==========
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Total Buildings", str(len(buildings)), f"/ {MAX_BUILDINGS} Max", "#00bcd4", "🏢")
with c2:
    total_floors = sum(b.get("", 0) for b in buildings)
    kpi_card("Total Floors", str(total_floors), "", "#4caf50", "🏗️")
with c3:
    kpi_card("Config Status", "" if get_config_path().exists() else "", "", "#ff9800", "💾")

st.markdown("")

# ========== UNIVERSITY & CAMPUS IDENTITY ==========
section_header("UNIVERSITY IDENTITY", "🏛️")

id_col1, id_col2 = st.columns(2)
with id_col1:
    uni_id = st.text_input("University ID", value=layout.get("", ""), key="")
    campus_id = st.text_input("Campus ID", value=layout.get("", ""), key="")
with id_col2:
    uni_name = st.text_input("University Name", value=layout.get("", "Bennett University"), key="")
    campus_name = st.text_input("Campus Name", value=layout.get("", "Main Campus"), key="")

st.markdown("")

# ========== ADD NEW BUILDING ==========
section_header("ADD NEW BUILDING", "➕")

if len(buildings) >= MAX_BUILDINGS:
    st.warning(
        f"Maximum limit of {MAX_BUILDINGS} buildings reached. "
        "Delete an existing building before adding a new one."
    )
else:
    with st.form("", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            new_bld_id = st.text_input(
                "Building ID (e.g., science_block)",
                help="Use lowercase with underscores, no spaces"
            )
        with fc2:
            new_bld_name = st.text_input(
                "Building Name (e.g., Science Block)",
                help="Human-readable display name"
            )
        with fc3:
            new_num_floors = st.number_input(
                "Number of Floors", min_value=1, max_value=20, value=2
            )

        submitted = st.form_submit_button("➕ Add Building", type="")
        if submitted:
            # Validation
            errors = []
            if not new_bld_id or not new_bld_id.strip():
                errors.append("Building ID cannot be empty.")
            elif " " in new_bld_id:
                errors.append("Building ID cannot contain spaces (use underscores).")
            elif any(b[""] == new_bld_id for b in buildings):
                errors.append(f"Building ID '{new_bld_id}' already exists.")

            if not new_bld_name or not new_bld_name.strip():
                errors.append("Building Name cannot be empty.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                new_building = {
                    "": new_bld_id.strip(),
                    "": new_bld_name.strip(),
                    "": int(new_num_floors),
                }
                buildings.append(new_building)
                layout[""] = buildings
                layout[""] = uni_id
                layout[""] = uni_name
                layout[""] = campus_id
                layout[""] = campus_name
                try:
                    save_campus_layout(layout)
                    st.success(f"✅ Building '{new_bld_name}' added and saved.")
                    st.rerun()
                except ValueError as ve:
                    st.error(str(ve))

st.markdown("")

# ========== CURRENT ARCHITECTURE ==========
section_header("CURRENT UNIVERSITY ARCHITECTURE", "🏢")

if not buildings:
    st.info("No buildings configured. Use the form above to add buildings.")
else:
    for i, bld in enumerate(buildings):
        bld_id = bld.get("", f"building_{i}")
        bld_name = bld.get("", bld_id.replace("", " ").title())
        bld_floors = bld.get("", 0)

        with st.expander(f"🏢 {bld_name} — ID: `{bld_id}` — {bld_floors} floor(s)", expanded=False):
            ec1, ec2, ec3 = st.columns([2, 2, 1])
            with ec1:
                st.markdown(f"**Building ID:** `{bld_id}`")
                st.markdown(f"**Building Name:** {bld_name}")
            with ec2:
                st.markdown(f"**Floors:** {bld_floors}")
            with ec3:
                if st.button("🗑️ Delete", key=f"del_{bld_id}_{i}"):
                    buildings.pop(i)
                    layout[""] = buildings
                    save_campus_layout(layout)
                    st.rerun()

st.markdown("")

# ========== SAVE ALL CONFIGURATION ==========
section_header("SAVE CONFIGURATION", "💾")

st.caption(
    "Click below to persist the university identity and building list. "
    "This does NOT modify the physics configuration or calibrated parameters."
)

if st.button("💾 SAVE CONFIGURATION", type="", width=""):
    layout[""] = uni_id
    layout[""] = uni_name
    layout[""] = campus_id
    layout[""] = campus_name
    layout[""] = buildings
    try:
        save_campus_layout(layout)
        st.success(f"✅ Configuration saved to `{get_config_path()}`")
    except ValueError as ve:
        st.error(str(ve))

# ========== INFO ==========
st.info(
    "**Note:** Changing the architecture here does not automatically generate telemetry data for new buildings. "
    "Run `scripts/generate_data.py` after adding buildings to produce matching simulation output."
)