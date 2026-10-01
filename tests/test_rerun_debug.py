import pytest
import os
import sys
from streamlit.testing.v1 import AppTest
from unittest.mock import patch
import pandas as pd

PAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "dashboard", "pages"))

def test_03_multiple_runs():
    at = AppTest.from_file(os.path.join(PAGES_DIR, "03_Security_Dashboard.py"))
    at.session_state["mqtt_client"] = None
    
    print("RUN 1")
    at.run(timeout=10)
    assert not at.exception
    
    print("RUN 2")
    at.run(timeout=10)
    assert not at.exception
    
    print("RUN 3")
    at.run(timeout=10)
    assert not at.exception
