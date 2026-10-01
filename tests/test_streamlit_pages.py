import pytest
import os
import sys
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock
import pandas as pd
from dashboard.data.campus_config import save_campus_layout

PAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "dashboard", "pages"))

@pytest.fixture
def empty_telemetry_mock():
    with patch("dashboard.data.loader.load_historical_data", return_value=pd.DataFrame()) as m:
        yield m

@pytest.fixture
def mock_telemetry():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=10, freq="h"),
        "location_id": ["campus.building.floor.room"] * 10,
        "is_manipulated": [False] * 8 + [True] * 2,
        "attack_id": [None] * 8 + ["atk1"] * 2,
        "attack_type": [None] * 8 + ["spoof"] * 2,
        "attack_target": [None] * 8 + ["reported_co2_ppm"] * 2,
        "reported_co2_ppm": [400] * 8 + [1500] * 2,
        "true_co2_ppm": [400] * 10,
        "observed_co2_ppm": [400] * 8 + [450] * 2,
        "attack_magnitude": [0] * 8 + [1100] * 2,
        "campus_id": ["campus"] * 10,
        "building_id": ["building"] * 10,
        "floor_id": ["floor"] * 10,
        "room_id": ["room"] * 10,
        "energy_interval_kwh": [10.0] * 10,
        "reported_power_kw": [5.0] * 10,
        "hvac_power_kw": [2.0] * 10,
        "occupancy": [10] * 10,
        "reported_temperature_c": [22.0] * 10
    })
    return df

def test_03_security_dashboard_empty_data(empty_telemetry_mock):
    at = AppTest.from_file(os.path.join(PAGES_DIR, "03_Security_Dashboard.py"))
    at.session_state["mqtt_client"] = None
    at.run(timeout=30)
    assert not at.exception, f"03 Security Dashboard crashed: {at.exception}"
    
    subheaders = [s.value for s in at.subheader]
    assert any("CYBERSECURITY & FDI MONITORING" in s for s in subheaders)
    
    md_text = " ".join([m.value for m in at.markdown])
    assert "Threat Level: **NORMAL**" in md_text
    
    warnings = [w.value for w in at.warning]
    assert any("No historical telemetry is currently available" in w for w in warnings)

def test_03_security_dashboard_no_attack(mock_telemetry):
    mock_telemetry["is_manipulated"] = False
    
    with patch("dashboard.data.loader.load_historical_data", return_value=mock_telemetry):
        at = AppTest.from_file(os.path.join(PAGES_DIR, "03_Security_Dashboard.py"))
        at.session_state["mqtt_client"] = None
        at.run(timeout=30)
        assert not at.exception, f"03 Security Dashboard crashed: {at.exception}"
        
        subheaders = [s.value for s in at.subheader]
        assert any("CYBERSECURITY & FDI MONITORING" in s for s in subheaders)
        
        md_text = " ".join([m.value for m in at.markdown])
        assert "Threat Level: **NORMAL**" in md_text

def test_03_security_dashboard_with_attack(mock_telemetry):
    with patch("dashboard.data.loader.load_historical_data", return_value=mock_telemetry):
        at = AppTest.from_file(os.path.join(PAGES_DIR, "03_Security_Dashboard.py"))
        at.session_state["mqtt_client"] = None
        at.run(timeout=30)
        assert not at.exception, f"03 Security Dashboard crashed: {at.exception}"
        
        subheaders = [s.value for s in at.subheader]
        assert any("CYBERSECURITY & FDI MONITORING" in s for s in subheaders)
        
        md_text = " ".join([m.value for m in at.markdown])
        assert "Threat Level: **WARNING**" in md_text or "Threat Level: **CRITICAL**" in md_text
        
        assert len(at.dataframe) > 0

def test_05_campus_configuration():
    with patch("dashboard.data.campus_config.load_campus_layout", return_value={}):
        at = AppTest.from_file(os.path.join(PAGES_DIR, "05_Campus_Configuration.py"))
        at.run(timeout=30)
        assert not at.exception, f"05 Campus Configuration crashed: {at.exception}"
        
        subheaders = [s.value for s in at.subheader]
        assert any("CAMPUS CONFIGURATION & TOPOLOGY" in s for s in subheaders)
        assert any("UNIVERSITY IDENTITY" in s for s in subheaders)
        
        # Test empty configuration defaults
        assert at.text_input("uni_id").value == "bu"

def test_04_what_if_simulation_empty(empty_telemetry_mock):
    at = AppTest.from_file(os.path.join(PAGES_DIR, "04_What_If_Simulation.py"))
    at.session_state["mqtt_client"] = None
    at.run(timeout=30)
    assert not at.exception, f"04 What-If Simulation crashed: {at.exception}"
    
    subheaders = [s.value for s in at.subheader]
    assert any("WHAT-IF SIMULATION: PHASE 5 PHYSICS" in s for s in subheaders)
    
def test_06_building_reports(mock_telemetry):
    with patch("dashboard.data.loader.load_historical_data", return_value=mock_telemetry):
        at = AppTest.from_file(os.path.join(PAGES_DIR, "06_Building_Reports.py"))
        at.run(timeout=30)
        assert not at.exception, f"06 Building Reports crashed: {at.exception}"
