import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

class DataCleaner:
    def __init__(self):
        pass
        
    def clean(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        report = {
            "initial_records": len(df),
            "duplicates_removed": 0,
            "invalid_records_removed": 0,
            "missing_stats": {}
        }
        
        # 1. Parse timestamps and handle timezone
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        # 2. Duplicate detection
        orig_len = len(df)
        df = df.drop_duplicates(subset=['timestamp', 'location_id'], keep='last')
        report["duplicates_removed"] = orig_len - len(df)
        
        # 3. Impossible value bounds detection (Set to NaN instead of dropping the whole row)
        if 'reported_temperature_c' in df.columns:
            invalid_temp = (df['reported_temperature_c'] < -50) | (df['reported_temperature_c'] > 60)
            df.loc[invalid_temp, 'reported_temperature_c'] = np.nan
            
        if 'reported_co2_ppm' in df.columns:
            invalid_co2 = (df['reported_co2_ppm'] < 300) | (df['reported_co2_ppm'] > 10000)
            df.loc[invalid_co2, 'reported_co2_ppm'] = np.nan
            
        if 'reported_power_kw' in df.columns:
            invalid_pwr = df['reported_power_kw'] < 0
            df.loc[invalid_pwr, 'reported_power_kw'] = np.nan
            
        if 'occupancy' in df.columns:
            invalid_occ = df['occupancy'] < 0
            df.loc[invalid_occ, 'occupancy'] = np.nan
        
        # 4. Missing value detection (explicitly reported, but NOT fabricated)
        for col in df.columns:
            missing_pct = df[col].isna().mean() * 100
            report["missing_stats"][col] = f"{missing_pct:.2f}%"
            
        report["final_records"] = len(df)
        
        # Sort chronologically
        df = df.sort_values(by=['location_id', 'timestamp']).reset_index(drop=True)
        
        return df, report
