import pytest
from dashboard.data.campus_config import save_campus_layout, load_campus_layout

def test_buildings_iteration_regression(tmp_path, monkeypatch):
    """
    Regression test to ensure buildings iteration correctly reads a list of dictionaries,
    and calculates the total floors properly without raising an AttributeError.
    """
    # Mock the config path to a temporary file
    mock_config_path = tmp_path / "university_layout.yaml"
    monkeypatch.setattr("dashboard.data.campus_config._CONFIG_PATH", mock_config_path)
    monkeypatch.setattr("dashboard.data.campus_config._CONFIG_DIR", tmp_path)

    layout = {
        "university_id": "bennett_uni",
        "university_name": "Bennett University",
        "campus_id": "main_campus",
        "campus_name": "Main Campus",
        "buildings": [
            {"id": "academic_block", "name": "Academic Block", "floors": 2},
            {"id": "science_block", "name": "Science Block", "floors": 3}
        ]
    }
    
    # Save layout
    save_campus_layout(layout)
    
    # Load layout
    loaded_layout = load_campus_layout()
    buildings = loaded_layout.get("buildings", [])
    
    # Assert buildings is a list of dicts
    assert isinstance(buildings, list)
    assert len(buildings) == 2
    assert all(isinstance(b, dict) for b in buildings)
    
    # Reproduce the logic in 05_Campus_Configuration.py that caused the crash
    total_floors = sum(b.get("floors", 0) for b in buildings)
    
    # Validate result
    assert total_floors == 5, f"Expected 5 total floors, got {total_floors}"
