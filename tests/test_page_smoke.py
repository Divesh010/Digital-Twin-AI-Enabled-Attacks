"""
Streamlit AppTest smoke tests for pages that show blank white screens.
These tests execute the actual Streamlit page code and detect runtime exceptions.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from streamlit.testing.v1 import AppTest
import pytest

PAGES_DIR = os.path.join(os.path.dirname(__file__), '..', 'src', 'dashboard', 'pages')


def test_security_dashboard_page_runs():
    """Security Dashboard must execute without exceptions."""
    page_path = os.path.join(PAGES_DIR, '03_Security_Dashboard.py')
    at = AppTest.from_file(page_path, default_timeout=60)
    at.run()
    # If there's an exception, print it for debugging
    if at.exception:
        for exc in at.exception:
            print(f"EXCEPTION: {type(exc).__name__}: {exc}")
    assert not at.exception, f"Security Dashboard raised: {at.exception}"


def test_campus_configuration_page_runs():
    """Campus Configuration must execute without exceptions."""
    page_path = os.path.join(PAGES_DIR, '05_Campus_Configuration.py')
    at = AppTest.from_file(page_path, default_timeout=30)
    at.run()
    if at.exception:
        for exc in at.exception:
            print(f"EXCEPTION: {type(exc).__name__}: {exc}")
    assert not at.exception, f"Campus Configuration raised: {at.exception}"
