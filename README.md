# Aerotrader Flight Pricing Simulator

Welcome to the Aerotrader Flight Pricing Simulator project! This repository provides a flexible, extensible framework for simulating stock price movement as aircraft flight, using real market data and aviation-inspired metaphors. The project is designed for researchers, educators, and quantitative traders interested in novel ways to visualize and analyze market behavior.

## Project Overview

- **Modular Engine (`modular/`)**: The main, production-ready simulation engine. Highly modular, with each component (data loading, turbulence, stall detection, etc.) separated for clarity and extensibility. Use this for robust research, backtesting, and advanced experimentation.
- **Standalone Scripts (`standalone/`)**: Experimental and legacy versions of the engine. These scripts are ideal for rapid prototyping, learning, and exploring different approaches to flight-based market simulation. Each version demonstrates a different stage of development or feature set.

## Key Features
- Simulates stock price movement as a "flight," with altitude, fuel, turbulence, and stall events mapped to market metrics.
- Supports both daily (macro cruise) and synthetic intraday (jet flight) simulation modes.
- Outputs detailed markdown and JSON logs, including flight summaries and telemetry tables.
- Generates printable reports with plots and candle phase tables.
- Modular design for easy extension and experimentation.

## Directory Structure
- `modular/` — Main modular engine, entry point, logs, and documentation
- `modular/core/` — All core simulation modules and logic
- `modular/logs/` — All simulation log output (markdown and JSON)
- `standalone/` — Experimental and legacy scripts for reference and prototyping
- `development/` — Progress logs, templates, and project management

## Getting Started

### Running the Modular Engine
Use the entry point for all simulations:
```bash
python modular/entry.py [--mode daily|intraday] [--ticker TICKER] [--date YYYY-MM-DD] [--log-format markdown|json]
```
Logs are saved to `modular/logs/`.

### Running Standalone Scripts
Navigate to the `standalone/` directory and run any of the `flight_sim_enginevX.py` scripts directly:
```bash
python standalone/flight_sim_enginev3.py
```
Logs are saved to `standalone/logs/`.

## Documentation
- See `modular/README.md` for detailed documentation of the modular engine and its modules.
- See `standalone/README.md` for descriptions of each standalone script.
- See `development/progress.log` for a changelog and project history.

## Intended Audience
- Quantitative researchers and traders
- Educators and students in finance or data science
- Developers interested in creative market simulation and visualization

## License
This project is open source and available under the MIT License.
