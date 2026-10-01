import pandas as pd
import numpy as np

class SimulationValidator:
    @staticmethod
    def validate(df: pd.DataFrame, config=None) -> dict:
        issues = []
        
        # Structural checks
        required_cols = [
            "timestamp", "location_id", "occupancy", "occupancy_pct",
            "true_co2_ppm", "true_temperature_c", "true_power_kw",
            "energy_interval_kwh", "energy_cumulative_kwh"
        ]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            issues.append(f"Missing columns: {missing}")
            
        if df.duplicated(subset=["timestamp", "location_id"]).any():
            issues.append("Duplicate timestamp/location_id combinations found")
            
        # Physical bounds
        if (df['occupancy_pct'] < 0).any() or (df['occupancy_pct'] > 100 + 1e-5).any():
            issues.append("Occupancy percentage out of bounds [0, 100]")
            
        if (df['true_co2_ppm'] < 0).any():
            issues.append("Negative CO2 found")
            
        if not np.isfinite(df['true_temperature_c']).all():
            issues.append("Non-finite temperatures found")
            
        if (df['true_power_kw'] < 0).any():
            issues.append("Negative power found")
            
        if (df['energy_interval_kwh'] < 0).any():
            issues.append("Negative interval energy found")
            
        # Consistency
        # total_power = base + light + plug + hvac
        calculated_power = df['base_power_kw'] + df['lighting_power_kw'] + df['plug_power_kw'] + df['hvac_power_kw']
        if not np.allclose(df['true_power_kw'], calculated_power, atol=1e-5):
            issues.append("Total power does not match sum of components")
            
        # monotonic energy check per room
        for room, grp in df.groupby('location_id'):
            if not grp['energy_cumulative_kwh'].is_monotonic_increasing:
                issues.append(f"Cumulative energy not monotonically increasing for room {room}")
                
        if config:
            duration_s = (config.simulation.end_datetime - config.simulation.start_datetime).total_seconds()
            expected_intervals = int(duration_s / config.simulation.dt_seconds)
            num_rooms = len(df['location_id'].unique())
            expected_rows = expected_intervals * num_rooms
            if len(df) != expected_rows:
                issues.append(f'Row count {len(df)} does not match expected {expected_rows}')
            if len(df['timestamp'].unique()) != expected_intervals:
                issues.append(f'Unique timestamps {len(df['timestamp'].unique())} does not match expected {expected_intervals}')
            for r, g in df.groupby('location_id'):
                if len(g) != expected_intervals:
                    issues.append(f'Room {r} has {len(g)} rows, expected {expected_intervals}')
        
        is_valid = len(issues) == 0
        return {
            "is_valid": is_valid,
            "issues": issues
        }



