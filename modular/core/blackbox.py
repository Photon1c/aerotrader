# blackbox.py

import json


def write_markdown_log(
    filepath,
    ticker,
    date,
    mode,
    gains,
    fuel,
    stalls,
    turbulence,
    timestamps,
    flight_phases,
    sync_data=None,
):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# ✈️ Flight Summary - {ticker} - {date}\n")
        f.write(f"- Mode: {mode}\n")
        f.write(f"- Net Gain: {gains[-1]:+.2f}%\n")
        f.write(f"- Max Altitude: {max(gains):+.2f}%\n")
        f.write(f"- Fuel Remaining: {fuel[-1]:.1f}%\n")
        f.write(f"- Stall Events: {sum(stalls)}\n")
        f.write(f"- Emergency Landings: 0\n")

        if sync_data and isinstance(sync_data, dict):
            f.write(
                f"- Sync Coefficient: {sync_data.get('synchronization_coefficient', 0.0)}\n"
            )
            f.write(f"- Regime: {sync_data.get('regime_label', 'N/A')}\n")
            f.write(
                f"- Execution Type: {sync_data.get('execution_type_label', 'N/A')}\n"
            )
            f.write(f"- Event Authorized: {sync_data.get('event_authorized', False)}\n")
            f.write(
                f"- Valve Saturation: {sync_data.get('valve_saturation_score', 0.0)}\n"
            )
            f.write(
                f"- Collective Risk: {sync_data.get('collective_execution_risk', 0.0)}\n"
            )
            f.write(
                f"- Reflexive Cascade Risk: {sync_data.get('reflexive_cascade_risk', 0.0)}\n"
            )

        f.write(
            "\n| Time  | Altitude (%) | Fuel (%) | Stall | Turbulence | Phase       | Status | Sync Sc | Regime          |\n"
        )
        f.write(
            "|-------|---------------|----------|--------|------------|-------------|--------|---------|-----------------|\n"
        )
        for i in range(len(gains)):
            status = (
                "Takeoff"
                if i == 0
                else ("Landed" if i == len(gains) - 1 else "Cruising")
            )
            sc = ""
            regime = ""
            if sync_data and isinstance(sync_data, dict):
                tele = sync_data.get("telemetry", [])
                if i < len(tele):
                    sc = f"{tele[i].get('synchronization_coefficient', 0.0):.2f}"
                    regime = tele[i].get("regime_label", "")[:15]
            f.write(
                f"| {timestamps[i]} | {gains[i]:+.2f}% | {fuel[i]:.1f}% | {'Yes' if stalls[i] else 'No'} | {turbulence[i]} | {flight_phases[i]:8} | {status:7} | {sc:>7} | {regime:<15} |\n"
            )

        if sync_data and sync_data.get("diagnostics"):
            f.write("\n### Synchronization Diagnostics\n\n")
            for note in sync_data["diagnostics"]:
                f.write(f"- {note}\n")


def write_json_log(
    filepath,
    ticker,
    date,
    mode,
    gains,
    fuel,
    stalls,
    turbulence,
    timestamps,
    flight_phases,
    sync_data=None,
):
    log = {
        "ticker": ticker,
        "date": date,
        "mode": mode,
        "net_gain": gains[-1],
        "max_altitude": max(gains),
        "fuel_remaining": fuel[-1],
        "stall_events": int(sum(stalls)),
        "emergency_landings": 0,
        "telemetry": [
            {
                "time": timestamps[i],
                "altitude": gains[i],
                "fuel": fuel[i],
                "stall": bool(stalls[i]),
                "turbulence": turbulence[i],
                "phase": flight_phases[i],
                "status": (
                    "Takeoff"
                    if i == 0
                    else ("Landed" if i == len(gains) - 1 else "Cruising")
                ),
            }
            for i in range(len(gains))
        ],
    }

    if sync_data:
        if isinstance(sync_data, dict):
            summary_fields = {
                "synchronization_coefficient": sync_data.get(
                    "synchronization_coefficient", 0.0
                ),
                "execution_type": sync_data.get("execution_type", "Type I"),
                "execution_type_label": sync_data.get(
                    "execution_type_label", "Distributed Execution"
                ),
                "regime_label": sync_data.get("regime_label", "DISTRIBUTED_CRUISE"),
                "event_authorized": sync_data.get("event_authorized", False),
                "event_authorization_confidence": sync_data.get(
                    "event_authorization_confidence", 0.0
                ),
                "absorption_capacity": sync_data.get("absorption_capacity", 1.0),
                "valve_saturation_score": sync_data.get("valve_saturation_score", 0.0),
                "queue_pressure": sync_data.get("queue_pressure", 0.0),
                "hidden_flow_suspected": sync_data.get("hidden_flow_suspected", False),
                "observed_dom_confidence": sync_data.get(
                    "observed_dom_confidence", 1.0
                ),
                "collective_execution_risk": sync_data.get(
                    "collective_execution_risk", 0.0
                ),
                "reflexive_cascade_risk": sync_data.get("reflexive_cascade_risk", 0.0),
            }
            log.update(summary_fields)
            if sync_data.get("diagnostics"):
                log["diagnostics"] = sync_data["diagnostics"]
        elif isinstance(sync_data, list):
            log["synchronization"] = sync_data

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def write_log(
    filepath,
    ticker,
    date,
    mode,
    gains,
    fuel,
    stalls,
    turbulence,
    timestamps,
    flight_phases,
    format="markdown",
    sync_data=None,
):
    if format == "json":
        write_json_log(
            filepath,
            ticker,
            date,
            mode,
            gains,
            fuel,
            stalls,
            turbulence,
            timestamps,
            flight_phases,
            sync_data,
        )
    else:
        write_markdown_log(
            filepath,
            ticker,
            date,
            mode,
            gains,
            fuel,
            stalls,
            turbulence,
            timestamps,
            flight_phases,
            sync_data,
        )
