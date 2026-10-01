"""
Campus Architecture Configuration Loader

Manages the user-defined university architecture layout
stored in data/configuration/university_layout.yaml.

This file is SEPARATE from the physics configuration
(config/root.yaml, config/campus.yaml) which controls
simulation parameters and calibrated values.

This configuration controls:
- University identity (name, ID)
- Campus identity (name, ID)
- Building definitions (ID, name, floor count)
- Maximum 16 buildings enforced

Other dashboard pages import load_campus_layout() to
read the persisted architecture.
"""

import yaml
from pathlib import Path
from typing import Optional

# Canonical path for the architecture configuration
_CONFIG_DIR = Path("data/configuration")
_CONFIG_PATH = _CONFIG_DIR / "university_layout.yaml"

# Hard limit per university architecture specification
MAX_BUILDINGS = 16


def _default_layout() -> dict:
    """Return the default campus layout when no config file exists."""
    return {
        "university_id": "bennett_uni",
        "university_name": "Bennett University",
        "campus_id": "main_campus",
        "campus_name": "Main Campus",
        "buildings": [],
    }


def load_campus_layout() -> dict:
    """Load the persisted university architecture layout.
    
    Returns the saved layout dict, or the default if no file exists.
    This function does NOT use Streamlit caching so it always
    reflects the latest saved state.
    """
    if not _CONFIG_PATH.exists():
        return _default_layout()
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return _default_layout()
        return data
    except Exception:
        return _default_layout()


def save_campus_layout(layout: dict) -> None:
    """Persist the university architecture layout to disk.
    
    Creates the directory if it doesn't exist.
    Validates the building count limit before saving.
    
    Raises:
        ValueError: if more than MAX_BUILDINGS buildings.
    """
    buildings = layout.get("buildings", [])
    if len(buildings) > MAX_BUILDINGS:
        raise ValueError(
            f"Cannot save: {len(buildings)} buildings exceeds "
            f"the maximum of {MAX_BUILDINGS}."
        )
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(layout, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get_config_path() -> Path:
    """Return the canonical configuration file path."""
    return _CONFIG_PATH
