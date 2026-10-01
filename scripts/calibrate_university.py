import argparse
import pandas as pd
import json
import yaml
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ingestion.adapter import DatasetAdapter
from ingestion.cleaner import DataCleaner
from calibration.calibrator import TwinCalibrator
from config.loader import load_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, required=True, help="Path to raw CSV dataset")
    parser.add_argument('--config', type=str, required=True, help="Path to YAML mapping config")
    parser.add_argument('--out', type=str, required=True, help="Output path for calibrated config JSON")
    parser.add_argument('--room-id', type=str, required=True, help="Room ID to calibrate")
    parser.add_argument('--building-id', type=str, required=True, help="Building ID")
    parser.add_argument('--val-out', type=str, required=True, help="Path to save the validation split CSV")
    
    args = parser.parse_args()
    
    with open(args.config, 'r') as f:
        mapping = yaml.safe_load(f)
        
    df = pd.read_csv(args.dataset)
    
    # 1. Ingestion / Mapping
    adapter = DatasetAdapter(mapping)
    canonical_df = adapter.apply(df)
    
    # 2. Cleaning
    cleaner = DataCleaner()
    clean_df, report = cleaner.clean(canonical_df)
    
    # 3. Calibration
    base_config = load_config('config/root.yaml')
    calibrator = TwinCalibrator(base_config, method='Powell')
    
    calibrated_config, val_df = calibrator.calibrate(clean_df, args.room_id, args.building_id, train_ratio=0.7)
    
    # Output Config
    with open(args.out, 'w') as f:
        f.write(calibrated_config.model_dump_json(indent=2))
        
    # Output Validation dataset
    val_df.to_csv(args.val_out, index=False)
    
    # Output report
    report_path = str(Path(args.out).with_suffix('.report.json'))
    full_report = {
        "cleaning": report,
        "calibration": calibrator.report
    }
    with open(report_path, 'w') as f:
        json.dump(full_report, f, indent=2)
        
    print(f"Calibration complete. Config saved to {args.out}")

if __name__ == '__main__':
    main()
