import pandas as pd
import numpy as np
from typing import Dict, Any
import matplotlib.pyplot as plt
import os
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config.models import RootConfig
from simulation.engine import DigitalTwinSimulator

class TwinValidator:
    def __init__(self, config: RootConfig, baseline_config: RootConfig = None):
        self.config = config
        self.baseline_config = baseline_config
        
    def validate(self, val_df: pd.DataFrame, out_dir: str) -> Dict[str, Any]:
        os.makedirs(out_dir, exist_ok=True)
        
        sim = DigitalTwinSimulator(self.config)
        sim_df = sim.simulate()
        
        baseline_df = None
        if self.baseline_config:
            baseline_sim = DigitalTwinSimulator(self.baseline_config)
            baseline_df = baseline_sim.simulate()
            baseline_df['timestamp'] = pd.to_datetime(baseline_df['timestamp'], utc=True)
        
        sim_df['timestamp'] = pd.to_datetime(sim_df['timestamp'], utc=True)
        val_df['timestamp'] = pd.to_datetime(val_df['timestamp'], utc=True)
        
        merged = pd.merge(val_df, sim_df, on=['timestamp', 'location_id'], suffixes=('_real', '_sim'))
        if len(merged) == 0:
            return {"error": "No overlapping timestamps between validation set and simulation"}
            
        metrics = {}
        
        def compute_metrics(real_col, sim_col, prefix):
            if real_col in merged.columns and sim_col in merged.columns:
                real = merged[real_col].dropna()
                sim = merged.loc[real.index, sim_col]
                
                if len(real) == 0: return
                
                mae = mean_absolute_error(real, sim)
                rmse = np.sqrt(mean_squared_error(real, sim))
                mape = np.mean(np.abs((real - sim) / (real + 1e-9))) * 100
                r2 = r2_score(real, sim)
                
                metrics[prefix] = {
                    "Calibrated_MAE": mae,
                    "Calibrated_RMSE": rmse,
                    "Calibrated_MAPE": mape,
                    "Calibrated_R2": r2
                }
                
                if baseline_df is not None:
                    baseline_merged = pd.merge(val_df, baseline_df, on=['timestamp', 'location_id'], suffixes=('_real', '_base'))
                    if sim_col.replace('_sim', '_base') in baseline_merged.columns:
                        base = baseline_merged.loc[real.index, sim_col.replace('_sim', '_base')]
                        metrics[prefix].update({
                            "Baseline_MAE": mean_absolute_error(real, base),
                            "Baseline_RMSE": np.sqrt(mean_squared_error(real, base)),
                            "Baseline_MAPE": np.mean(np.abs((real - base) / (real + 1e-9))) * 100,
                            "Baseline_R2": r2_score(real, base),
                            "Improvement_RMSE_Pct": (np.sqrt(mean_squared_error(real, base)) - rmse) / (np.sqrt(mean_squared_error(real, base)) + 1e-9) * 100
                        })
                
                plt.figure(figsize=(10,4))
                plt.plot(merged['timestamp'], merged[real_col], label='Real Measurement', alpha=0.7)
                plt.plot(merged['timestamp'], merged[sim_col], label='Calibrated Twin', alpha=0.7)
                if baseline_df is not None and sim_col.replace('_sim', '_base') in baseline_merged.columns:
                    plt.plot(merged['timestamp'], baseline_merged[sim_col.replace('_sim', '_base')], label='Baseline Twin', alpha=0.5, linestyle='--')
                plt.title(f'Actual vs Simulated {prefix}')
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, f'actual_vs_simulated_{prefix}.png'))
                plt.close()

        compute_metrics('reported_power_kw_real', 'reported_power_kw_sim', 'Power')
        compute_metrics('reported_temperature_c_real', 'reported_temperature_c_sim', 'Temperature')
        compute_metrics('reported_co2_ppm_real', 'reported_co2_ppm_sim', 'CO2')
        compute_metrics('energy_interval_kwh_real', 'energy_interval_kwh_sim', 'Energy')
        
        pd.DataFrame(metrics).to_csv(os.path.join(out_dir, 'metrics.csv'))
        
        return metrics
