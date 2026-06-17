# flight_sim_engine.py
from datetime import datetime
import pandas as pd
import time
import argparse
import os

from .data_loader import load_stock_data, load_option_data
from .flight_path import compute_altitude_series
from .fuel_gauge import compute_fuel_levels
from .stall_detector import detect_stalls
from .turbulence_sensor import detect_iv_turbulence
from .blackbox import write_log
from .synchronization import (
    compute_synchronization,
    estimate_price_displacement,
    estimate_volume_spike_ratio,
    estimate_volatility_expansion,
)
from .crow_simulator import compute_flock_state

# --- CLI Config ---
parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode",
    choices=["daily", "intraday"],
    default="daily",
    help="Flight simulation mode",
)
parser.add_argument("--ticker", type=str, default="SPY", help="Ticker symbol")
parser.add_argument("--date", type=str, help="Simulation date (YYYY-MM-DD)")
parser.add_argument(
    "--log-format",
    type=str,
    default="markdown",
    choices=["markdown", "json"],
    help="Log output format",
)
args = parser.parse_args()
MODE = args.mode
TICKER = args.ticker
LOG_FORMAT = args.log_format

if args.date:
    sim_date = pd.to_datetime(args.date)
else:
    sim_date = None

# Set logs directory to the existing /modular/logs
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../logs"))
OUTPUT_PATH = os.path.join(
    LOGS_DIR, f"flight_log_{TICKER.lower()}.{'json' if LOG_FORMAT == 'json' else 'md'}"
)

# --- ASCII Plane Takeoff Animation (Single Line) ---
plane = "✈️"
runway_length = 35
print("\nPreparing for takeoff...")
for i in range(runway_length):
    print("\r" + " " * i + plane, end="", flush=True)
    time.sleep(0.12)
print("\r" + " " * (runway_length + 2), end="\r")  # Clear the line after animation
print("🛫 Takeoff complete!\n")

# --- Load Data ---
stock_df = load_stock_data(TICKER)
option_df = load_option_data(TICKER)

# --- Preprocess Stock Data ---
stock_df["Date"] = pd.to_datetime(stock_df["Date"])
stock_df = stock_df.sort_values("Date")
stock_df["Close/Last"] = pd.to_numeric(stock_df["Close/Last"], errors="coerce")
stock_df["Volume"] = pd.to_numeric(stock_df["Volume"], errors="coerce")

from .candle_interpreter import apply_interpretation

if MODE == "daily":
    # --- Select Sampled Dates (last 5) ---
    if sim_date is not None:
        sampled = stock_df[stock_df["Date"] == sim_date].copy()
        if sampled.empty:
            raise ValueError(f"No data for {TICKER} on {sim_date.date()}")
    else:
        sampled = stock_df.tail(5).copy()
    prices = sampled["Close/Last"]
    volumes = sampled["Volume"]
    iv_series = pd.to_numeric(option_df["IV"], errors="coerce").dropna()
    stalls = detect_stalls(prices, sampled, iv_series)
    turbulence = detect_iv_turbulence(iv_series, sampled)
    from .fuel_gauge import generate_intraday_fuel_curve

    fuel = generate_intraday_fuel_curve(len(sampled))
    # For daily, use close-to-close gain as "altitude"
    altitudes = (prices.pct_change().fillna(0).cumsum() * 100).tolist()
    timestamps = (
        sampled["Date"].dt.strftime("%H:%M").tolist()
        if "Date" in sampled
        else [str(i) for i in range(len(sampled))]
    )
    flight_phases = apply_interpretation(sampled)["Flight Phase"].tolist()
    mode_label = "Macro Cruise (Daily)"

elif MODE == "intraday":
    # --- Use only the last candle or specified date for intraday emulation ---
    if sim_date is not None:
        sampled = stock_df[stock_df["Date"] == sim_date].copy()
        if sampled.empty:
            raise ValueError(f"No data for {TICKER} on {sim_date.date()}")
    else:
        sampled = stock_df.tail(1).copy()
    from .intraday_emulator import simulate_intraday_path
    from .microturbulence import estimate_intraday_iv
    from .fuel_gauge import generate_intraday_fuel_curve

    candle = sampled.iloc[0]
    intraday_flight = simulate_intraday_path(candle)  # returns dict
    timestamps = list(intraday_flight.keys())
    altitudes = list(intraday_flight.values())
    fuel = generate_intraday_fuel_curve(len(altitudes))
    stalls = [False for _ in altitudes]  # Placeholder: no EMA stalls in this mode yet
    turbulence = estimate_intraday_iv(option_df.tail(1))[: len(altitudes)]
    # Infer flight phases from the full candle
    flight_phases = [apply_interpretation(sampled).iloc[0]["Flight Phase"]] * len(
        altitudes
    )
    mode_label = "Jet Flight (Intraday)"
else:
    raise ValueError(f"Unknown mode: {MODE}")

# --- Synchronization Analysis ---
sync_result = compute_synchronization(
    price_displacement=estimate_price_displacement(prices.tolist())
    if MODE == "daily"
    else (altitudes[-1] - altitudes[-2] if len(altitudes) > 1 else 0.0),
    volume_spike_ratio=estimate_volume_spike_ratio(volumes.tolist())
    if MODE == "daily"
    else 1.0,
    volatility_expansion=estimate_volatility_expansion(
        iv_series.diff().iloc[-1] if len(iv_series) > 1 else 0, iv_series.std()
    )
    if MODE == "daily"
    else 0.0,
    cvd_acceleration=0.0,
    prior_cruise_deviation=abs(altitudes[-1] - altitudes[0]) / 100.0
    if len(altitudes) > 1
    else 0.0,
    cvd_trend_strong=False,
    price_bounded_while_cvd_trends=False,
    event_proximity_minutes=float("inf"),
    event_type="unknown",
)

flock_state = compute_flock_state(sync_result)

sync_output = sync_result.to_dict()
sync_output["telemetry"] = []
for i in range(len(altitudes)):
    step_sync = compute_synchronization(
        price_displacement=altitudes[i] - altitudes[i - 1] if i > 0 else 0.0,
        volume_spike_ratio=estimate_volume_spike_ratio(volumes.tolist()[: i + 1])
        if MODE == "daily"
        else 1.0,
        volatility_expansion=0.0,
    )
    sync_output["telemetry"].append(step_sync.to_dict())

print(f"\nSynchronization Coefficient: {sync_result.synchronization_coefficient:.4f}")
print(f"Regime: {sync_result.regime_label}")
print(f"Execution Type: {sync_result.execution_type_label}")
print(f"Event Authorized: {sync_result.event_authorized}")
print(f"Valve Saturation: {sync_result.valve_saturation_score:.2f}")
print(f"Collective Execution Risk: {sync_result.collective_execution_risk:.2f}")
print(f"Reflexive Cascade Risk: {sync_result.reflexive_cascade_risk:.2f}")

if sync_result.diagnostics:
    print("\nDiagnostics:")
    for note in sync_result.diagnostics:
        print(f"  - {note}")

print("\nCrow Flock State:")
print(f"  Flock Sync: {flock_state.flock_synchronization:.2f}")
print(f"  Scout Alert: {flock_state.scout_alert_active}")
print(f"  Flock Type: {flock_state.flock_execution_type}")

# --- Verbose Output ---
print("\nTurbulence Profile:")
print(turbulence)
if (
    isinstance(turbulence, list)
    and len(turbulence) > 0
    and isinstance(turbulence[0], str)
):
    print(
        f"Heavy: {turbulence.count('Heavy')}, Moderate: {turbulence.count('Moderate')}, Calm: {turbulence.count('Calm')}"
    )

print("\nStall Events:")
print(stalls)
print(f"Total Stalls: {sum(stalls)} / {len(stalls)}")

# --- Write Output ---
write_log(
    filepath=OUTPUT_PATH,
    ticker=TICKER,
    date=(
        sim_date.strftime("%m/%d/%Y")
        if sim_date is not None
        else datetime.today().strftime("%m/%d/%Y")
    ),
    mode=mode_label,
    gains=altitudes,
    fuel=fuel,
    stalls=stalls,
    turbulence=turbulence,
    timestamps=timestamps,
    flight_phases=flight_phases,
    format=LOG_FORMAT,
    sync_data=sync_output,
)

print("\nStall Events:")
print(stalls)
print(f"Total Stalls: {sum(stalls)} / {len(stalls)}")

# --- Write Output ---
write_log(
    filepath=OUTPUT_PATH,
    ticker=TICKER,
    date=(
        sim_date.strftime("%m/%d/%Y")
        if sim_date is not None
        else datetime.today().strftime("%m/%d/%Y")
    ),
    mode=mode_label,
    gains=altitudes,
    fuel=fuel,
    stalls=stalls,
    turbulence=turbulence,
    timestamps=timestamps,
    flight_phases=flight_phases,
    format=LOG_FORMAT,
)

print(f"[✓] Flight log saved to {OUTPUT_PATH}")
print(f"🔗 Sample Log: [`{OUTPUT_PATH}`](./{OUTPUT_PATH})")

# --- Display Candle Interpreter Table as Markdown ---
if MODE == "daily":
    interpreted_table = apply_interpretation(sampled)
    print("\n🕯️ Candle Phase Summary:")
    print("| Date       | Close    | Phase     |")
    print("|------------|----------|-----------|")
    for _, row in interpreted_table.iterrows():
        print(
            f"| {row['Date'].strftime('%Y-%m-%d')} | {row['Close/Last']:.2f}   | {row['Flight Phase']:<9} |"
        )
elif MODE == "intraday":
    print("\n🕯️ Candle Phase Summary:")
    print("| Time   | Altitude (%) | Phase     |")
    print("|--------|--------------|-----------|")
    for i, t in enumerate(timestamps):
        print(f"| {t} | {altitudes[i]:+.2f}       | {flight_phases[i]:<9} |")
