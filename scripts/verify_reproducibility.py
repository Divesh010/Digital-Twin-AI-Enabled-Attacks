import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from config.loader import load_config
from simulation.engine import DigitalTwinSimulator

config = load_config("config/root.yaml")
config.simulation.end_datetime = config.simulation.start_datetime + pd.Timedelta(days=1)

print("Running Sim A (Seed 42)...")
config.simulation.random_seed = 42
df_a = DigitalTwinSimulator(config).simulate()

print("Running Sim B (Seed 42)...")
config.simulation.random_seed = 42
df_b = DigitalTwinSimulator(config).simulate()

print("Running Sim C (Seed 99)...")
config.simulation.random_seed = 99
df_c = DigitalTwinSimulator(config).simulate()

cols_to_check = [
    'occupancy', 'occupancy_pct', 'plug_power_kw', 
    'observed_temperature_c', 'observed_co2_ppm', 'observed_power_kw'
]

print("\n--- REPRODUCIBILITY REPORT ---")
print("A (42) vs B (42):")
for col in cols_to_check:
    diff_count = (df_a[col] != df_b[col]).sum()
    print(f"  {col}: {diff_count} differing cells")

print("\nA (42) vs C (99):")
for col in cols_to_check:
    diff_count = (df_a[col] != df_c[col]).sum()
    status = "STOCHASTIC (differs)" if diff_count > 0 else "DETERMINISTIC (identical)"
    print(f"  {col}: {diff_count} differing cells -> {status}")
