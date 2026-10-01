import pandas as pd
from pathlib import Path
import streamlit as st
from config.loader import load_config
from config.models import RootConfig

@st.cache_data
def load_historical_data() -> pd.DataFrame:
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return pd.DataFrame()
        
    csv_files = list(outputs_dir.glob("*/telemetry.csv"))
    if not csv_files:
        return pd.DataFrame()
        
    latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
    
    df = pd.read_csv(latest_csv, low_memory=False)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

@st.cache_data
def load_app_config() -> RootConfig:
    return load_config("config/root.yaml")

@st.cache_data
def get_hierarchy(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    hierarchy = {}
    for campus in df['campus_id'].unique():
        hierarchy[campus] = {}
        campus_df = df[df['campus_id'] == campus]
        for building in campus_df['building_id'].unique():
            hierarchy[campus][building] = {}
            b_df = campus_df[campus_df['building_id'] == building]
            for floor in b_df['floor_id'].unique():
                f_df = b_df[b_df['floor_id'] == floor]
                hierarchy[campus][building][floor] = list(f_df['room_id'].unique())
    return hierarchy

def deduplicate_telemetry(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.drop_duplicates(subset=["timestamp", "location_id"], keep="last")