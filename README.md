# Bennett University — Smart Campus Digital Twin

This project implements a Phase 5 Digital Twin simulator and FDI (False Data Injection) attack research environment for a smart campus ecosystem. It simulates building physics (HVAC, thermodynamics, CO2, occupancy, energy usage), provides a unified canonical telemetry pipeline, and offers an interactive desktop UI for system analysis and security research.

## Architecture

1. **Digital Twin Simulator**: Object-oriented models (`src/models/`) simulating campus physics, driven by configuration files (`configs/`).
2. **Data Ingestion & Calibration**: Framework (`src/calibration/`) to ingest real-world telemetry (`data/raw/`), standardize it, and calibrate the simulator's thermal/occupancy parameters using mathematical optimization.
3. **FDI Attack Engine**: Security research layer (`src/attacks/`) that intercepts and maliciously modifies telemetry using defined attack vectors (offset, slow-drip, replay).
4. **Transport**: Local mock MQTT broker (`src/transport/`) mimicking real IoT publishing.
5. **Dashboard**: A Streamlit web application (`src/dashboard/`) visualizing real-time metrics, historical telemetry, and security events.
6. **Desktop App**: An Electron-based desktop shell (`desktop/`) that manages the Streamlit Python subprocess, dynamically allocates ports, and ensures robust process-tree lifecycle management.

## Directory Structure

```text
SmartCampusDigitalTwin/
├── config/              # Base system configurations
├── configs/             # Specific scenario/dataset configs
├── data/
│   ├── raw/             # Raw ingestion telemetry (drop external real datasets here)
│   ├── processed/       # Processed/normalized datasets
│   └── external/        # External mappings or metadata
├── desktop/             # Electron shell application
├── outputs/             # Generated simulation and research artifacts
├── scripts/             # Utility and helper scripts
├── src/
│   ├── attacks/         # FDI attack definitions and injection engine
│   ├── calibration/     # Data ingestion and parameter calibration
│   ├── dashboard/       # Streamlit UI pages
│   ├── models/          # Core physics and entity simulators
│   ├── simulation/      # Simulation execution engine
│   └── transport/       # MQTT broker and transport logic
├── tests/               # Pytest suite
├── .gitignore
├── requirements.txt
└── README.md
```

## Python Setup

1. Ensure Python 3.12+ is installed.
2. Create and activate a virtual environment (optional but recommended).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## How to Run Tests

From the project root:
```bash
$env:PYTHONPATH="src"
python -m pytest tests/ -v
```

## How to Run Streamlit Dashboard (Standalone)

From the project root:
```bash
$env:PYTHONPATH="src"
python -m streamlit run src/dashboard/app.py
```

## How to Run Electron Desktop App

1. Ensure Node.js and NPM are installed.
2. Install Electron dependencies (only needed once):
   ```bash
   npm --prefix desktop install
   ```
3. Start the application:
   ```bash
   npm --prefix desktop start
   ```
*Note: This automatically launches the Streamlit backend in a headless configuration and cleans up the process tree when the application window is closed.*

## How to Add a Real Dataset

1. Place your raw dataset files (e.g., CSV) into `data/raw/`.
2. Define a dataset configuration YAML file in `configs/datasets/` identifying the timestamp formats, hierarchy mapping, and columns.
3. Run the ingestion adapter to clean and output normalized standard telemetry into `data/processed/`.

## How to Run Calibration

1. Ensure a processed dataset is available.
2. Execute the calibration pipeline script. The script uses bounded numerical optimization (e.g., `scipy.optimize.minimize`) to tune physical parameters (like base load, mass, thermal leakage) against the empirical data.
3. The optimizer evaluates `J(theta) = w_power * RMSE(...)` until convergence.

## How to Run Validation

1. Split your temporal dataset into `train` and `test` splits.
2. Calibrate parameters using the `train` split.
3. Simulate the same temporal window on the `test` split using the tuned parameters and compute the baseline divergence error.

## Project Status

* **Digital Twin**: complete
* **MQTT**: complete
* **FDI attack engine**: complete
* **GUI**: complete
* **Electron desktop shell**: complete
* **Real-data ingestion**: complete
* **Calibration framework**: complete
* **Real-data validation**: pending
* **FDI detection research**: pending
