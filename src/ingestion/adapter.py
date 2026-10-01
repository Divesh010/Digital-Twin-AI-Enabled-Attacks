import pandas as pd
from typing import Dict, Any

class DatasetAdapter:
    def __init__(self, mapping: Dict[str, Any]):
        """
        mapping: dict mapping canonical names to source dataset column names or static values.
        Example:
        {
            "timestamp": "Datetime",
            "building_id": "BuildingName",
            "room_id": "RoomID",
            "energy_kwh": "Electricity",
            "temperature_c": "TempC",
            "university_id": "__STATIC__Bennett",
            "campus_id": "__STATIC__MainCampus",
            "delta_t_hours": 1.0  # Optional, for energy to power conversion
        }
        """
        self.mapping = mapping

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        canonical = pd.DataFrame()
        
        # Mapping base metadata
        canonical['timestamp'] = self._get_col(df, 'timestamp')
        canonical['university_id'] = self._get_col(df, 'university_id', 'unknown_univ')
        canonical['campus_id'] = self._get_col(df, 'campus_id', 'unknown_campus')
        canonical['building_id'] = self._get_col(df, 'building_id', 'unknown_building')
        canonical['room_id'] = self._get_col(df, 'room_id', 'unknown_room')
        
        # Floor ID can be derived from room if not present, or just 'unknown'
        canonical['floor_id'] = self._get_col(df, 'floor_id', 'unknown_floor')
        
        # Create full location_id
        canonical['location_id'] = (
            canonical['university_id'] + "." + 
            canonical['campus_id'] + "." + 
            canonical['building_id'] + "." + 
            canonical['floor_id'] + "." + 
            canonical['room_id']
        )
        
        # Map physics variables to REPORTED variables. We do NOT populate true_*
        if 'temperature_c' in self.mapping:
            canonical['reported_temperature_c'] = self._get_col(df, 'temperature_c')
        if 'co2_ppm' in self.mapping:
            canonical['reported_co2_ppm'] = self._get_col(df, 'co2_ppm')
        if 'occupancy' in self.mapping:
            canonical['occupancy'] = self._get_col(df, 'occupancy')
            
        # Power & Energy conversion
        if 'power_kw' in self.mapping:
            canonical['reported_power_kw'] = self._get_col(df, 'power_kw')
        
        if 'energy_kwh' in self.mapping:
            canonical['energy_interval_kwh'] = self._get_col(df, 'energy_kwh')
            if 'power_kw' not in self.mapping and 'delta_t_hours' in self.mapping:
                # Convert Energy to Power safely
                canonical['reported_power_kw'] = canonical['energy_interval_kwh'] / float(self.mapping['delta_t_hours'])

        # Explicitly tag as real data
        canonical['data_source'] = "REAL"
        
        return canonical

    def _get_col(self, df: pd.DataFrame, canonical_key: str, default: Any = None) -> pd.Series:
        if canonical_key not in self.mapping:
            if default is not None:
                return pd.Series([default] * len(df))
            raise ValueError(f"Required mapping key missing: {canonical_key}")
            
        val = self.mapping[canonical_key]
        if isinstance(val, str) and val.startswith('__STATIC__'):
            return pd.Series([val.split('__STATIC__')[1]] * len(df), index=df.index)
        
        if val in df.columns:
            return df[val].copy()
            
        raise ValueError(f"Column '{val}' mapped to '{canonical_key}' not found in DataFrame")
