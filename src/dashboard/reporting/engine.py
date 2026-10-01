"""
Building Report Engine

Reusable report generation module for the Smart Campus Digital Twin.
Accepts a building filter, time range, and aggregation period,
and returns aggregated metrics from actual telemetry data.

Supported periods:
  - Hour:     single calendar hour
  - Day:      single calendar day
  - Week:     Monday–Sunday (ISO week convention)
  - Month:    calendar month
  - Vacation: explicit start/end dates provided by the user
  - Custom:   arbitrary start/end date range

This module does NOT fabricate data. If no telemetry exists for
a building, the report clearly indicates missing data.
"""

import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from dashboard.styles import CARBON_FACTOR_KG_PER_KWH


@dataclass
class ReportMetrics:
    """Aggregated metrics for a building report."""
    building_id: str
    building_name: str
    period_label: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_energy_kwh: float = 0.0
    avg_power_kw: float = 0.0
    peak_power_kw: float = 0.0
    total_carbon_kg: float = 0.0
    avg_occupancy: float = 0.0
    peak_occupancy: int = 0
    hvac_energy_kwh: float = 0.0
    room_count: int = 0
    record_count: int = 0
    total_possible_records: int = 0
    data_completeness_pct: float = 0.0
    has_data: bool = False
    fdi_event_count: int = 0
    aggregated_df: Optional[pd.DataFrame] = field(default=None, repr=False)


def filter_telemetry(
    df: pd.DataFrame,
    building_id: str,
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
) -> pd.DataFrame:
    """Filter telemetry DataFrame by building and optional time range."""
    if df.empty:
        return df

    filtered = df[df["building_id"] == building_id].copy()

    if start_dt is not None:
        start_dt = pd.Timestamp(start_dt, tz="UTC") if pd.Timestamp(start_dt).tz is None else pd.Timestamp(start_dt)
        filtered = filtered[filtered["timestamp"] >= start_dt]

    if end_dt is not None:
        end_dt = pd.Timestamp(end_dt, tz="UTC") if pd.Timestamp(end_dt).tz is None else pd.Timestamp(end_dt)
        filtered = filtered[filtered["timestamp"] <= end_dt]

    return filtered


def aggregate_by_period(
    df: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    """Aggregate telemetry by the specified time period.

    Args:
        df: Filtered telemetry DataFrame (must have 'timestamp' column).
        period: One of 'Hourly', 'Daily', 'Weekly', 'Monthly'.

    Returns:
        DataFrame grouped by time_group with aggregated columns.
    """
    if df.empty:
        return df

    working = df.copy()

    if period == "Hourly":
        working["time_group"] = working["timestamp"].dt.floor("h")
    elif period == "Daily":
        working["time_group"] = working["timestamp"].dt.floor("D")
    elif period == "Weekly":
        # ISO week convention: Monday = start of week
        working["time_group"] = working["timestamp"].dt.to_period("W").apply(
            lambda r: r.start_time
        )
    elif period == "Monthly":
        working["time_group"] = working["timestamp"].dt.to_period("M").apply(
            lambda r: r.start_time
        )
    else:
        # Default to daily
        working["time_group"] = working["timestamp"].dt.floor("D")

    agg_dict = {}
    if "energy_interval_kwh" in working.columns:
        agg_dict["energy_interval_kwh"] = "sum"
    if "reported_power_kw" in working.columns:
        agg_dict["reported_power_kw"] = "mean"
    if "occupancy" in working.columns:
        agg_dict["occupancy"] = "mean"
    if "reported_co2_ppm" in working.columns:
        agg_dict["reported_co2_ppm"] = "mean"
    if "reported_temperature_c" in working.columns:
        agg_dict["reported_temperature_c"] = "mean"
    if "hvac_power_kw" in working.columns:
        agg_dict["hvac_power_kw"] = "mean"
    if "is_manipulated" in working.columns:
        agg_dict["is_manipulated"] = "sum"

    if not agg_dict:
        return pd.DataFrame()

    result = working.groupby("time_group").agg(agg_dict).reset_index()
    return result


def generate_report(
    df: pd.DataFrame,
    building_id: str,
    building_name: str,
    period: str,
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
    dt_seconds: int = 300,
) -> ReportMetrics:
    """Generate a building report from telemetry data.

    Args:
        df: Full telemetry DataFrame.
        building_id: Building to filter on.
        building_name: Display name for the building.
        period: Aggregation period label (e.g., 'Daily', 'Hourly').
        start_dt: Optional start datetime for filtering.
        end_dt: Optional end datetime for filtering.
        dt_seconds: Simulation timestep (for HVAC energy calculation).

    Returns:
        ReportMetrics dataclass with all computed values.
    """
    metrics = ReportMetrics(
        building_id=building_id,
        building_name=building_name,
        period_label=period,
        start_time=start_dt,
        end_time=end_dt,
    )

    filtered = filter_telemetry(df, building_id, start_dt, end_dt)

    if filtered.empty:
        return metrics

    metrics.has_data = True
    metrics.record_count = len(filtered)
    metrics.room_count = filtered["room_id"].nunique() if "room_id" in filtered.columns else 0

    # Energy
    if "energy_interval_kwh" in filtered.columns:
        metrics.total_energy_kwh = filtered["energy_interval_kwh"].sum()
        metrics.total_carbon_kg = metrics.total_energy_kwh * CARBON_FACTOR_KG_PER_KWH

    # Power
    if "reported_power_kw" in filtered.columns:
        metrics.avg_power_kw = filtered["reported_power_kw"].mean()
        metrics.peak_power_kw = filtered["reported_power_kw"].max()

    # Occupancy
    if "occupancy" in filtered.columns:
        metrics.avg_occupancy = filtered["occupancy"].mean()
        metrics.peak_occupancy = int(filtered["occupancy"].max())

    # HVAC
    if "hvac_power_kw" in filtered.columns:
        metrics.hvac_energy_kwh = filtered["hvac_power_kw"].sum() * (dt_seconds / 3600.0)

    # FDI
    if "is_manipulated" in filtered.columns:
        metrics.fdi_event_count = int(filtered["is_manipulated"].sum())

    # Data completeness estimate
    if start_dt and end_dt:
        total_seconds = (pd.Timestamp(end_dt) - pd.Timestamp(start_dt)).total_seconds()
        expected_records = max(1, total_seconds / dt_seconds) * metrics.room_count
        metrics.total_possible_records = int(expected_records)
        metrics.data_completeness_pct = min(100.0, (metrics.record_count / expected_records) * 100) if expected_records > 0 else 0.0
    else:
        metrics.total_possible_records = metrics.record_count
        metrics.data_completeness_pct = 100.0

    # Aggregated time-series
    metrics.aggregated_df = aggregate_by_period(filtered, period)

    return metrics
