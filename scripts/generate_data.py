import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config.loader import load_config
from simulation.engine import DigitalTwinSimulator
from quality.validator import SimulationValidator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    sim = DigitalTwinSimulator(config)
    df = sim.simulate()
    
    val_report = SimulationValidator.validate(df, config)
    
    duration_s = (config.simulation.end_datetime - config.simulation.start_datetime).total_seconds()
    total_sim_hours = duration_s / 3600.0
    expected_rows = int(duration_s / config.simulation.dt_seconds) * len(sim.rooms)
    
    mean_true_power = df['true_power_kw'].mean() # float64
    room_energies = df.groupby("location_id")['energy_interval_kwh'].sum()
    mean_room_energy = room_energies.mean()
    reconstructed_mean_room_energy = mean_true_power * total_sim_hours
    
    abs_err = abs(mean_room_energy - reconstructed_mean_room_energy)
    
    print("\n--- FULL PRECISION ENERGY RECONCILIATION ---")
    print(f"Mean True Power (kW)        : {mean_true_power:.12f}")
    print(f"Total Sim Hours             : {total_sim_hours:.12f}")
    print(f"Reconstructed Mean Room (kWh): {reconstructed_mean_room_energy:.12f}")
    print(f"Actual Mean Room (kWh)       : {mean_room_energy:.12f}")
    print(f"Absolute Error              : {abs_err:.12e}")
    assert abs_err < 1e-9, f"Energy reconciliation failed! Error: {abs_err}"
    
    print("\n--- FINAL AUDIT REPORT ---")
    print(f"Dataset      : {len(df)} records (expected {expected_rows}), {len(df.location_id.unique())} rooms, dt={config.simulation.dt_seconds}s, duration={total_sim_hours}h")
    print(f"Occupancy    : min={df.occupancy.min()}, mean={df.occupancy.mean():.2f}, max={df.occupancy.max()}")
    print(f"CO2 (ppm)    : min={df.true_co2_ppm.min():.1f}, mean={df.true_co2_ppm.mean():.1f}, max={df.true_co2_ppm.max():.1f}, p95={df.true_co2_ppm.quantile(0.95):.1f}")
    print(f"Temp (C)     : min={df.true_temperature_c.min():.2f}, mean={df.true_temperature_c.mean():.2f}, max={df.true_temperature_c.max():.2f}")
    print(f"Power (kW)   : min={df.true_power_kw.min():.2f}, mean={mean_true_power:.2f}, max={df.true_power_kw.max():.2f}")
    print(f"Energy (kWh) : campus_total={df.energy_interval_kwh.sum():.2f}, mean_room={mean_room_energy:.2f}, median_room={room_energies.median():.2f}, min_room={room_energies.min():.2f}, max_room={room_energies.max():.2f}")
    
    hvac_dist = df.hvac_state.value_counts(normalize=True) * 100
    print("HVAC Freq    :", ", ".join([f"{k}={v:.1f}%" for k, v in hvac_dist.items()]))
    hvac_power = df.groupby("hvac_state")['hvac_power_kw'].mean()
    print("HVAC Power   :", ", ".join([f"{k}={v:.2f}kW" for k, v in hvac_power.items()]))
    
    print(f"Validation   : {'PASS' if val_report['is_valid'] else 'FAIL'}")
    if not val_report['is_valid']:
        for issue in val_report['issues']:
            print(f"  - {issue}")
            
    out_dir = Path("outputs") / sim.sim_run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "telemetry.csv", index=False)

if __name__ == '__main__':
    main()
