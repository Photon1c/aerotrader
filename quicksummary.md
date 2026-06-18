# Aerotrader v1.1 — Quick Reference for LLMs

## Project Overview
A flight-metaphor trading simulator. Market data is modeled as aircraft: altitude = % gain, fuel = liquidity, stalls/turbulence = risk signals. The v0.4.0 upgrade adds synchronization modeling for collective execution events.

## Directory Layout
```
aerotraderv1.1/
├── quicksummary.md              ← this file
├── modular/                     ← production code
│   ├── entry.py                 ← CLI entry: `python entry.py --mode daily --ticker SPY`
│   ├── settings.json            ← data paths, tickers
│   ├── logs/                    ← flight log output (JSON or markdown)
│   ├── tests/
│   │   └── test_synchronization.py  ← 18 tests for sync module
│   └── core/
│       ├── flight_sim_engine.py ← main simulation engine (CLI-driven)
│       ├── synchronization.py   ← S_c coeff, execution types, event auth, cruise mode
│       ├── crow_simulator.py    ← flock model mirroring market sync
│       ├── blackbox.py          ← log writer (markdown + JSON)
│       ├── flight_ops_core.py   ← cross-domain orchestrator (market/aircraft/traffic)
│       ├── data_loader.py       ← CSV stock + option data loading
│       ├── flight_path.py       ← altitude (% gain) computation
│       ├── fuel_gauge.py        ← fuel (liquidity) modeling
│       ├── stall_detector.py    ← stall risk detection
│       ├── turbulence_sensor.py ← turbulence classification (Calm/Moderate/Heavy)
│       ├── candle_interpreter.py← candle phase (Thrust/Stall/Go-around/Hover)
│       ├── intraday_emulator.py ← 5-step intraday path from OHLC
│       ├── microturbulence.py   ← mock intraday IV estimation
│       ├── chart_creator.py     ← matplotlib charting
│       └── generate_flight_report.py ← report generator
├── standalone/                  ← legacy/experimental scripts
└── development/
    ├── upgrade.md               ← original upgrade spec
    └── progress.log             ← changelog
```

## Main Commands

```bash
# Run daily simulation (last 5 candles)
cd modular
python entry.py --mode daily --ticker SPY --log-format json

# Run for a specific date
python entry.py --mode daily --ticker SPY --date 2025-06-27

# Run intraday emulation
python entry.py --mode intraday --ticker SPY

# Run with markdown output (default)
python entry.py --mode daily --ticker SPY --log-format markdown

# Generate report from latest log
python core/generate_flight_report.py

# Run all 18 synchronization tests
python -m pytest tests/test_synchronization.py -v
# or directly:
python tests/test_synchronization.py
```

## Key Architecture

### Synchronization Module (`synchronization.py`)
| Concept | Description |
|---------|-------------|
| **S_c** | Synchronization Coefficient (0.0–1.0). Weighted composite of price, CVD, volume, spread, volatility, event proximity, cruise deviation |
| **Type I** | Distributed Execution — normal dispersed flow (S_c < 0.30) |
| **Type II** | Collective Execution — shared trigger (S_c ≥ 0.30) |
| **Type III** | Reflexive Collective — self-reinforcing cascade (S_c ≥ 0.65 + queue pressure + volatility) |
| **E_a** | Event Authorization — catalyst that permits latent pressure release |
| **Cruise Mode** | Pressure being absorbed/metabolized (not inactivity) |

### Output Schema (JSON)
```json
{
  "ticker": "SPY",
  "synchronization_coefficient": 0.1583,
  "execution_type": "Type I",
  "execution_type_label": "Distributed Execution",
  "regime_label": "STABLE_CRUISE",
  "event_authorized": false,
  "valve_saturation_score": 0.0,
  "queue_pressure": 0.0,
  "hidden_flow_suspected": false,
  "observed_dom_confidence": 1.0,
  "collective_execution_risk": 0.0,
  "reflexive_cascade_risk": 0.0,
  "absorption_capacity": 1.0,
  "diagnostics": [],
  "telemetry": [
    { "time": "...", "altitude": 0.0, "fuel": 100.0, "stall": false,
      "turbulence": "Calm", "phase": "Thrust", "status": "Takeoff" }
  ]
}
```

### Regime Labels
| Label | S_c Range | Meaning |
|-------|-----------|---------|
| STABLE_CRUISE | 0.00–0.30 | Normal, no synchronization |
| PRESSURE_ACCUMULATION | 0.00–0.30 | CVD trends while price bounded |
| PERSISTENCE_DECAY | 0.10–0.30 | Residual sync dissipating |
| STEP_CLIMB | 0.30–0.65 | Upward flight-level transition (positive displacement) |
| STEP_DESCENT | 0.30–0.65 | Downward flight-level transition (negative displacement) |
| ALTITUDE_TRANSITION | 0.30–0.65 | Active move between bands (bounded displacement) |
| COLLECTIVE_EXECUTION_MANEUVER | 0.65–1.00 | Synchronized collective move |
| REFLEXIVE_CASCADE | 0.65–1.00 | Self-reinforcing cascade |
| FLIGHT_LEVEL_STABILIZATION | any | Post-CEM equilibrium establishment |
| FAILED_RESTORATION | any | Stabilization attempt failed, pressure persists |

### Crow Flock Bridge (`crow_simulator.py`)
| Market Concept | Crow Equivalent |
|----------------|-----------------|
| Type I | Scattered foraging |
| Type II | Flock synchronized movement |
| Type III | Panic cascade |
| Event Authorization | Scout alert |
| S_c | Flock synchronization |
| Queue pressure | Roost pressure |

### Backward Compatibility
- `write_log()` accepts optional `sync_data=None` — omitting it produces pre-upgrade output
- `FlightState.sync` defaults to zeroed `SynchronizationResult`
- All report generation handles missing sync fields gracefully
