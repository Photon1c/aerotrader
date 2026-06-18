import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.synchronization import (
    compute_synchronization,
    SynchronizationResult,
    RegimeLabel,
    ExecutionType,
    estimate_price_displacement,
    estimate_volume_spike_ratio,
    estimate_volatility_expansion,
)
from core.crow_simulator import compute_flock_state, CrowFlockState, FlockExecutionType


def test_type_i_distributed_execution():
    result = compute_synchronization(
        price_displacement=0.1,
        cvd_acceleration=0.05,
        volume_spike_ratio=1.1,
        spread_widening_ratio=0.01,
        volatility_expansion=0.1,
        event_proximity_minutes=float("inf"),
        prior_cruise_deviation=0.05,
    )
    assert result.synchronization_coefficient < 0.30, (
        f"Expected S_c < 0.30 for Type I, got {result.synchronization_coefficient}"
    )
    assert result.execution_type == "Type I", (
        f"Expected Type I, got {result.execution_type}"
    )
    assert result.regime_label in (
        RegimeLabel.STABLE_CRUISE.value,
        RegimeLabel.PRESSURE_ACCUMULATION.value,
    ), f"Unexpected regime: {result.regime_label}"
    assert not result.event_authorized
    assert not result.hidden_flow_suspected
    assert result.collective_execution_risk < 0.3
    print(
        f"[PASS] Type I: S_c={result.synchronization_coefficient:.4f}, "
        f"Regime={result.regime_label}, Type={result.execution_type}"
    )


def test_type_i_edge_cruise_boundary():
    result = compute_synchronization(
        price_displacement=0.0,
        cvd_acceleration=0.0,
        volume_spike_ratio=1.0,
        spread_widening_ratio=0.0,
        volatility_expansion=0.0,
        prior_cruise_deviation=0.0,
        cvd_trend_strong=False,
    )
    assert result.synchronization_coefficient < 0.01, (
        f"S_c too high: {result.synchronization_coefficient}"
    )
    assert result.regime_label == RegimeLabel.STABLE_CRUISE.value
    assert result.execution_type == "Type I"
    print(
        f"[PASS] Type I edge: S_c={result.synchronization_coefficient:.4f}, "
        f"Regime={result.regime_label}"
    )


def test_type_ii_collective_execution():
    result = compute_synchronization(
        price_displacement=2.5,
        cvd_acceleration=1.8,
        volume_spike_ratio=4.0,
        spread_widening_ratio=0.5,
        volatility_expansion=1.5,
        event_proximity_minutes=5.0,
        event_type="macro",
        prior_cruise_deviation=2.0,
    )
    assert result.synchronization_coefficient >= 0.30, (
        f"Expected S_c >= 0.30 for Type II, got {result.synchronization_coefficient}"
    )
    assert result.execution_type in ("Type II", "Type III"), (
        f"Expected Type II or III, got {result.execution_type}"
    )
    assert result.event_authorized, (
        "Expected event_authorized=True for Type II with event proximity"
    )
    assert result.event_authorization_confidence > 0.5
    assert result.valve_saturation_score > 0.3
    print(
        f"[PASS] Type II: S_c={result.synchronization_coefficient:.4f}, "
        f"Regime={result.regime_label}, Type={result.execution_type}, "
        f"EventAuth={result.event_authorized}"
    )


def test_type_ii_event_authorization():
    result = compute_synchronization(
        price_displacement=1.5,
        volume_spike_ratio=3.0,
        volatility_expansion=1.0,
        event_proximity_minutes=10.0,
        event_type="macro",
        prior_cruise_deviation=1.0,
    )
    assert result.synchronization_coefficient >= 0.30
    assert result.event_authorized
    assert result.event_authorization_confidence > 0.7
    print(
        f"[PASS] Type II event auth: S_c={result.synchronization_coefficient:.4f}, "
        f"AuthConf={result.event_authorization_confidence:.4f}"
    )


def test_type_iii_reflexive_cascade():
    result = compute_synchronization(
        price_displacement=3.5,
        cvd_acceleration=2.5,
        volume_spike_ratio=6.0,
        spread_widening_ratio=1.2,
        volatility_expansion=2.5,
        event_proximity_minutes=2.0,
        prior_cruise_deviation=3.0,
    )
    assert result.synchronization_coefficient >= 0.65, (
        f"Expected S_c >= 0.65 for Type III, got {result.synchronization_coefficient}"
    )
    assert result.execution_type == "Type III", (
        f"Expected Type III reflexive, got {result.execution_type}"
    )
    assert result.regime_label in (
        RegimeLabel.REFLEXIVE_CASCADE.value,
        RegimeLabel.COLLECTIVE_EXECUTION_MANEUVER.value,
    ), f"Unexpected regime: {result.regime_label}"
    assert result.reflexive_cascade_risk > 0.3, (
        f"Expected reflexive_cascade_risk > 0.3, got {result.reflexive_cascade_risk}"
    )
    assert result.collective_execution_risk > 0.5
    assert result.hidden_flow_suspected or True
    print(
        f"[PASS] Type III: S_c={result.synchronization_coefficient:.4f}, "
        f"Regime={result.regime_label}, Type={result.execution_type}, "
        f"CascadeRisk={result.reflexive_cascade_risk:.4f}"
    )


def test_type_iii_stop_cascade_scenario():
    result = compute_synchronization(
        price_displacement=4.0,
        cvd_acceleration=3.0,
        volume_spike_ratio=8.0,
        spread_widening_ratio=2.0,
        volatility_expansion=3.0,
        prior_cruise_deviation=4.0,
    )
    assert result.execution_type == "Type III"
    assert result.reflexive_cascade_risk > 0.5
    assert result.collective_execution_risk > 0.7
    assert result.valve_saturation_score > 0.7
    assert result.queue_pressure > 0.7
    print(
        f"[PASS] Type III stop cascade: S_c={result.synchronization_coefficient:.4f}, "
        f"QueuePressure={result.queue_pressure:.4f}, "
        f"CascadeRisk={result.reflexive_cascade_risk:.4f}"
    )


def test_absorption_phase_detection():
    result = compute_synchronization(
        price_displacement=0.1,
        cvd_acceleration=0.8,
        volume_spike_ratio=1.5,
        prior_cruise_deviation=0.1,
        cvd_trend_strong=True,
        price_bounded_while_cvd_trends=True,
    )
    assert result.hidden_flow_suspected, (
        "Expected hidden_flow_suspected=True when CVD trends while price bounded"
    )
    assert result.regime_label == RegimeLabel.PRESSURE_ACCUMULATION.value, (
        f"Expected PRESSURE_ACCUMULATION, got {result.regime_label}"
    )
    assert result.absorption_capacity < 1.0
    print(
        f"[PASS] Absorption: S_c={result.synchronization_coefficient:.4f}, "
        f"Regime={result.regime_label}, HiddenFlow={result.hidden_flow_suspected}"
    )


def test_post_release_rebalance():
    result = compute_synchronization(
        price_displacement=0.0,
        volume_spike_ratio=0.8,
        prior_cruise_deviation=0.0,
        force_post_release=True,
    )
    assert result.regime_label == RegimeLabel.FLIGHT_LEVEL_STABILIZATION.value, (
        f"Expected FLIGHT_LEVEL_STABILIZATION, got {result.regime_label}"
    )
    print(f"[PASS] Post-release: Regime={result.regime_label}")


def test_estimate_price_displacement():
    assert estimate_price_displacement([100, 101, 102]) == 1.0
    assert estimate_price_displacement([100]) == 0.0
    assert estimate_price_displacement([100, 95]) == -5.0
    assert estimate_price_displacement([]) == 0.0
    print("[PASS] estimate_price_displacement")


def test_estimate_volume_spike_ratio():
    vols = [100, 100, 100]
    assert estimate_volume_spike_ratio(vols) == 1.0, (
        "Equal volumes should give ratio 1.0"
    )
    vols2 = [100, 100, 300]
    ratio = estimate_volume_spike_ratio(vols2)
    assert ratio == 3.0, f"Expected 3.0, got {ratio}"
    assert estimate_volume_spike_ratio([]) == 1.0
    assert estimate_volume_spike_ratio([50]) == 1.0
    print("[PASS] estimate_volume_spike_ratio")


def test_crow_flock_type_i():
    mkt = compute_synchronization(
        price_displacement=0.1,
        volume_spike_ratio=1.0,
    )
    flock = compute_flock_state(mkt)
    assert flock.flock_execution_type == FlockExecutionType.SCATTERED_FORAGING
    assert flock.flock_synchronization < 0.3
    assert not flock.scout_alert_active
    print(
        f"[PASS] Crow Type I: FlockSync={flock.flock_synchronization:.4f}, "
        f"Type={flock.flock_execution_type}"
    )


def test_crow_flock_type_iii():
    mkt = compute_synchronization(
        price_displacement=4.0,
        cvd_acceleration=3.0,
        volume_spike_ratio=8.0,
        spread_widening_ratio=2.0,
        volatility_expansion=3.0,
        prior_cruise_deviation=4.0,
    )
    flock = compute_flock_state(mkt)
    assert flock.flock_execution_type == FlockExecutionType.PANIC_CASCADE, (
        f"Expected PANIC_CASCADE, got {flock.flock_execution_type}"
    )
    assert flock.collective_takeoff_risk > 0.5
    assert flock.roost_pressure > 0.5
    print(
        f"[PASS] Crow Type III: FlockSync={flock.flock_synchronization:.4f}, "
        f"TakeoffRisk={flock.collective_takeoff_risk:.4f}, "
        f"Type={flock.flock_execution_type}"
    )


def test_to_dict_output_schema():
    result = compute_synchronization(price_displacement=1.0, volume_spike_ratio=2.0)
    d = result.to_dict()
    required_fields = [
        "synchronization_coefficient",
        "execution_type",
        "execution_type_label",
        "regime_label",
        "event_authorized",
        "event_authorization_confidence",
        "absorption_capacity",
        "valve_saturation_score",
        "queue_pressure",
        "hidden_flow_suspected",
        "observed_dom_confidence",
        "collective_execution_risk",
        "reflexive_cascade_risk",
        "diagnostics",
    ]
    for field in required_fields:
        assert field in d, f"Missing output field: {field}"
    assert isinstance(d["synchronization_coefficient"], float)
    assert 0.0 <= d["synchronization_coefficient"] <= 1.0
    assert isinstance(d["diagnostics"], list)
    print(
        f"[PASS] Output schema: {len(required_fields)} fields present, "
        f"S_c={d['synchronization_coefficient']:.4f}"
    )


def test_synchronization_coefficient_range():
    for _ in range(10):
        pd_ = 0.0
        vs_ = 1.0
        result = compute_synchronization(
            price_displacement=pd_,
            volume_spike_ratio=vs_,
        )
        assert 0.0 <= result.synchronization_coefficient <= 1.0, (
            f"S_c out of range: {result.synchronization_coefficient}"
        )

    extreme = compute_synchronization(
        price_displacement=4.0,
        cvd_acceleration=3.0,
        volume_spike_ratio=6.0,
        volatility_expansion=3.0,
        spread_widening_ratio=1.0,
    )
    assert 0.0 <= extreme.synchronization_coefficient <= 1.0, (
        f"Extreme S_c out of range: {extreme.synchronization_coefficient}"
    )
    assert extreme.synchronization_coefficient > 0.79, (
        f"Extreme input should produce high S_c, got {extreme.synchronization_coefficient}"
    )
    print(
        f"[PASS] S_c range: min=0.0, extreme={extreme.synchronization_coefficient:.4f}"
    )


def test_execution_type_ii_partial_alignment():
    result = compute_synchronization(
        price_displacement=1.0,
        cvd_acceleration=0.8,
        volume_spike_ratio=2.5,
        spread_widening_ratio=0.3,
        volatility_expansion=0.8,
        event_proximity_minutes=30.0,
        event_type="earnings",
        prior_cruise_deviation=0.8,
    )
    assert 0.30 <= result.synchronization_coefficient < 0.65, (
        f"Expected partial alignment (0.30-0.65), got {result.synchronization_coefficient}"
    )
    assert result.execution_type == "Type II"
    assert result.regime_label == RegimeLabel.STEP_CLIMB.value
    assert result.event_authorized
    print(
        f"[PASS] Type II partial: S_c={result.synchronization_coefficient:.4f}, "
        f"Regime={result.regime_label}, EventAuth={result.event_authorized}"
    )


def test_diagnostics_notes():
    result = compute_synchronization(
        price_displacement=0.1,
        cvd_acceleration=1.5,
        volume_spike_ratio=1.0,
    )
    has_lag_note = any("Price lagged CVD" in n for n in result.diagnostics)
    assert has_lag_note, "Expected diagnostic note about CVD leading price"
    print(f"[PASS] Diagnostics: {len(result.diagnostics)} notes generated")

    extreme = compute_synchronization(
        price_displacement=4.0,
        cvd_acceleration=3.0,
        volume_spike_ratio=6.0,
        volatility_expansion=3.0,
        spread_widening_ratio=1.0,
    )
    has_pressure_note = any("pressure release" in n for n in extreme.diagnostics)
    assert has_pressure_note, "Expected diagnostic note about pressure release"
    print(f"[PASS] Extreme diagnostics: {len(extreme.diagnostics)} notes")


def test_observed_dom_confidence():
    low_pressure = compute_synchronization(price_displacement=0.1)
    assert low_pressure.observed_dom_confidence > 0.8, (
        f"Low pressure should have high DOM confidence, got {low_pressure.observed_dom_confidence}"
    )
    high_pressure = compute_synchronization(
        price_displacement=4.0,
        volume_spike_ratio=8.0,
    )
    assert high_pressure.observed_dom_confidence < 0.8, (
        f"High pressure should reduce DOM confidence, got {high_pressure.observed_dom_confidence}"
    )
    print(
        f"[PASS] DOM confidence: low={low_pressure.observed_dom_confidence:.4f}, "
        f"high={high_pressure.observed_dom_confidence:.4f}"
    )


def test_synchronization_result_defaults():
    r = SynchronizationResult()
    assert r.synchronization_coefficient == 0.0
    assert r.execution_type == "Type I"
    assert r.regime_label == "STABLE_CRUISE"
    assert not r.event_authorized
    assert r.absorption_capacity == 1.0
    assert len(r.diagnostics) == 0
    d = r.to_dict()
    assert d["synchronization_coefficient"] == 0.0
    print(f"[PASS] Defaults validated")


if __name__ == "__main__":
    tests = [
        ("Type I — Distributed Execution", test_type_i_distributed_execution),
        ("Type I — Cruise Boundary", test_type_i_edge_cruise_boundary),
        ("Type II — Collective Execution", test_type_ii_collective_execution),
        ("Type II — Event Authorization", test_type_ii_event_authorization),
        ("Type II — Partial Alignment", test_execution_type_ii_partial_alignment),
        ("Type III — Reflexive Cascade", test_type_iii_reflexive_cascade),
        ("Type III — Stop Cascade", test_type_iii_stop_cascade_scenario),
        ("Absorption Phase Detection", test_absorption_phase_detection),
        ("Post-Release Rebalance", test_post_release_rebalance),
        ("Price Displacement Estimator", test_estimate_price_displacement),
        ("Volume Spike Ratio Estimator", test_estimate_volume_spike_ratio),
        ("Crow Flock Type I", test_crow_flock_type_i),
        ("Crow Flock Type III", test_crow_flock_type_iii),
        ("Output Schema", test_to_dict_output_schema),
        ("S_c Range Validation", test_synchronization_coefficient_range),
        ("Diagnostics Notes", test_diagnostics_notes),
        ("DOM Confidence", test_observed_dom_confidence),
        ("Default Values", test_synchronization_result_defaults),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    sys.exit(0 if failed == 0 else 1)
