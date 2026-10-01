import argparse
import pandas as pd
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from config.models import RootConfig
from calibration.validator import TwinValidator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, required=True, help="Path to cleaned validation CSV dataset")
    parser.add_argument('--calibration', type=str, required=True, help="Path to calibrated config JSON")
    parser.add_argument('--out-dir', type=str, required=True, help="Output directory for metrics and plots")
    parser.add_argument('--baseline-config', type=str, required=False, help="Path to original uncalibrated config JSON")
    
    args = parser.parse_args()
    
    # Load calibrated config
    with open(args.calibration, 'r') as f:
        config_data = json.load(f)
    config = RootConfig(**config_data)
    
    baseline_config = None
    if args.baseline_config:
        if args.baseline_config.endswith('.yaml') or args.baseline_config.endswith('.yml'):
            import yaml
            with open(args.baseline_config, 'r') as f:
                base_data = yaml.safe_load(f)
        else:
            with open(args.baseline_config, 'r') as f:
                base_data = json.load(f)
        baseline_config = RootConfig(**base_data)
    
    # Validation dataset (already cleaned canonical telemetry holdout)
    val_df = pd.read_csv(args.dataset)
    
    # Sync simulation time to the validation set
    val_df['timestamp'] = pd.to_datetime(val_df['timestamp'], utc=True)
    config.simulation.start_datetime = val_df['timestamp'].min()
    config.simulation.end_datetime = val_df['timestamp'].max()
    
    if baseline_config:
        baseline_config.simulation.start_datetime = val_df['timestamp'].min()
        baseline_config.simulation.end_datetime = val_df['timestamp'].max()
    
    validator = TwinValidator(config, baseline_config)
    metrics = validator.validate(val_df, args.out_dir)
    
    with open(os.path.join(args.out_dir, 'validation_report.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Validation complete. Results saved to {args.out_dir}")

if __name__ == '__main__':
    main()
