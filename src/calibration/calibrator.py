import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
from copy import deepcopy
from typing import Dict, List, Any, Tuple
import json
import hashlib
from datetime import datetime

from config.models import RootConfig
from simulation.engine import DigitalTwinSimulator

class TwinCalibrator:
    def __init__(self, config: RootConfig, method: str = 'Powell'):
        self.base_config = config
        self.method = method
        self.report = {}
        
    def _split_data(self, df: pd.DataFrame, train_ratio: float = 0.7) -> Tuple[pd.DataFrame, pd.DataFrame]:
        # Chronological split
        unique_times = np.sort(df['timestamp'].unique())
        split_idx = int(len(unique_times) * train_ratio)
        if split_idx == 0 or split_idx == len(unique_times):
            return df, pd.DataFrame()
            
        split_time = unique_times[split_idx]
        train = df[df['timestamp'] < split_time]
        val = df[df['timestamp'] >= split_time]
        return train, val

    def calibrate(self, df: pd.DataFrame, target_room_id: str, bld_id: str, train_ratio: float = 0.7) -> Tuple[RootConfig, pd.DataFrame]:
        train_df, val_df = self._split_data(df, train_ratio)
        
        # We will calibrate parameters for the specific room.
        # Find room config
        room_cfg = None
        for c in self.base_config.campus.buildings:
            if c.id == bld_id:
                for f in c.floors:
                    for r in f.rooms:
                        if r.id == target_room_id:
                            room_cfg = r
                            break
        
        if room_cfg is None:
            raise ValueError(f"Room {target_room_id} not found in config")
            
        # Initial Heuristic Guesses
        # These are just initial values x0 for the optimizer, not the final methodology.
        pwr_data = train_df['reported_power_kw'].dropna() if 'reported_power_kw' in train_df.columns else pd.Series()
        max_pwr = pwr_data.max() if len(pwr_data) > 0 else 5.0
        min_pwr = pwr_data.quantile(0.05) if len(pwr_data) > 0 else 0.1
        
        occ_data = train_df['occupancy'].dropna() if 'occupancy' in train_df.columns else pd.Series()
        max_occ = int(occ_data.max()) if len(occ_data) > 0 else 10
        
        # Identifiable parameters mapping: 
        # (name, initial_guess, bounds_min, bounds_max)
        params_to_opt = []
        
        if len(pwr_data) > 0:
            params_to_opt.append(('base_load_kw', min_pwr, 0.0, max_pwr))
            params_to_opt.append(('lighting_capacity_kw', (max_pwr - min_pwr)*0.5, 0.0, max_pwr))
            
        if 'reported_temperature_c' in train_df.columns:
            params_to_opt.append(('thermal_resistance_c_w', room_cfg.temperature.thermal_resistance_c_w, 0.001, 1.0))
            
        if 'reported_co2_ppm' in train_df.columns:
            params_to_opt.append(('ventilation_rate_m3_s', room_cfg.co2.ventilation_rate_m3_s, 0.0, 5.0))
            
        if not params_to_opt:
            self.report['status'] = "NO_IDENTIFIABLE_PARAMS"
            return self.base_config, val_df

        x0 = [p[1] for p in params_to_opt]
        bounds = [(p[2], p[3]) for p in params_to_opt]
        param_names = [p[0] for p in params_to_opt]
        
        self.report = {
            "dataset_hash": hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest(),
            "train_period": [str(train_df['timestamp'].min()), str(train_df['timestamp'].max())],
            "val_period": [str(val_df['timestamp'].min()), str(val_df['timestamp'].max())],
            "initial_parameters": {p[0]: p[1] for p in params_to_opt},
            "bounds": {p[0]: [p[2], p[3]] for p in params_to_opt},
            "optimization_method": self.method
        }
        
        # Create a tiny simulation config strictly for the training period to make optimization fast
        opt_config = deepcopy(self.base_config)
        orig_tz = self.base_config.simulation.start_datetime.tzinfo
        opt_config.simulation.start_datetime = train_df['timestamp'].min().tz_convert(orig_tz)
        # Cap train simulation to max 3 days to avoid slow optimizer loops
        train_end = min(train_df['timestamp'].max(), train_df['timestamp'].min() + pd.Timedelta(days=3))
        opt_config.simulation.end_datetime = train_end.tz_convert(orig_tz)
        
        # Performance isolation: Strip all other buildings/rooms from opt_config
        target_bld_idx, target_flr_idx, target_rm_idx = -1, -1, -1
        for bi, b in enumerate(opt_config.campus.buildings):
            if b.id == bld_id:
                for fi, f in enumerate(b.floors):
                    for ri, r in enumerate(f.rooms):
                        if r.id == target_room_id:
                            target_bld_idx, target_flr_idx, target_rm_idx = bi, fi, ri
                            break
        if target_bld_idx != -1:
            isolated_bld = deepcopy(opt_config.campus.buildings[target_bld_idx])
            isolated_flr = deepcopy(isolated_bld.floors[target_flr_idx])
            isolated_flr.rooms = [isolated_flr.rooms[target_rm_idx]]
            isolated_bld.floors = [isolated_flr]
            opt_config.campus.buildings = [isolated_bld]

        eval_count = [0]
        
        best_obj = [float('inf')]
        
        def objective(x):
            eval_count[0] += 1
            # Apply parameters
            temp_cfg = deepcopy(opt_config)
            tr = temp_cfg.campus.buildings[0].floors[0].rooms[0]
            
            for i, name in enumerate(param_names):
                val = x[i]
                if name == 'base_load_kw': tr.power.base_load_kw = val
                elif name == 'lighting_capacity_kw': tr.power.lighting_capacity_kw = val
                elif name == 'thermal_resistance_c_w': tr.temperature.thermal_resistance_c_w = val
                elif name == 'ventilation_rate_m3_s': tr.co2.ventilation_rate_m3_s = val
                
            sim = DigitalTwinSimulator(temp_cfg)
            sim_df = sim.simulate()
            
            # Merge
            sim_df['timestamp'] = pd.to_datetime(sim_df['timestamp'], utc=True)
            merged = pd.merge(train_df, sim_df, on=['timestamp', 'location_id'], suffixes=('_real', '_sim'))
            
            if len(merged) == 0:
                return 1e9
                
            # Compute Normalized RMSE
            rmse_total = 0.0
            
            if 'reported_power_kw_real' in merged.columns and 'reported_power_kw_sim' in merged.columns:
                real = merged['reported_power_kw_real']
                sim = merged['reported_power_kw_sim']
                rmse = np.sqrt(np.mean((real - sim)**2))
                nrmse = rmse / (real.mean() + 1e-9)
                rmse_total += nrmse * 1.0
                
            if 'reported_temperature_c_real' in merged.columns and 'reported_temperature_c_sim' in merged.columns:
                real = merged['reported_temperature_c_real']
                sim = merged['reported_temperature_c_sim']
                rmse = np.sqrt(np.mean((real - sim)**2))
                nrmse = rmse / (real.mean() + 1e-9)
                rmse_total += nrmse * 0.5
                
            if 'reported_co2_ppm_real' in merged.columns and 'reported_co2_ppm_sim' in merged.columns:
                real = merged['reported_co2_ppm_real']
                sim = merged['reported_co2_ppm_sim']
                rmse = np.sqrt(np.mean((real - sim)**2))
                nrmse = rmse / (real.mean() + 1e-9)
                rmse_total += nrmse * 0.5
                
            if rmse_total < best_obj[0]:
                best_obj[0] = rmse_total
                if eval_count[0] % 50 == 0:
                    print(f"Eval {eval_count[0]}: Best OBJ = {best_obj[0]:.4f}")
                
            return rmse_total

        # Run optimization
        import time
        start_time = time.time()
        initial_obj = objective(x0)
        res = minimize(objective, x0, method=self.method, bounds=bounds, options={'maxiter': 20})
        
        final_obj = objective(res.x)
        elapsed = time.time() - start_time
        
        self.report["initial_objective_value"] = initial_obj
        self.report["final_objective_value"] = final_obj
        self.report["optimization_status"] = res.message if hasattr(res, 'message') else 'Unknown'
        self.report["evaluations"] = eval_count[0]
        self.report["elapsed_seconds"] = elapsed
        self.report["optimized_parameters"] = {param_names[i]: float(res.x[i]) for i in range(len(param_names))}
        self.report["optimization_status"] = "SUCCESS" if res.success else "FAILED: " + str(res.message)
        
        # Apply to final config
        final_config = deepcopy(self.base_config)
        tr = None
        for b in final_config.campus.buildings:
            for f in b.floors:
                for r in f.rooms:
                    if r.id == target_room_id:
                        tr = r
                        break
                        
        for i, name in enumerate(param_names):
            val = res.x[i]
            if name == 'base_load_kw': tr.power.base_load_kw = val
            elif name == 'lighting_capacity_kw': tr.power.lighting_capacity_kw = val
            elif name == 'thermal_resistance_c_w': tr.temperature.thermal_resistance_c_w = val
            elif name == 'ventilation_rate_m3_s': tr.co2.ventilation_rate_m3_s = val
            
        return final_config, val_df
