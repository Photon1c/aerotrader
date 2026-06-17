from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import math


class ExecutionType(Enum):
    TYPE_I = "Type I"
    TYPE_II = "Type II"
    TYPE_III = "Type III"


class RegimeLabel(Enum):
    DISTRIBUTED_CRUISE = "DISTRIBUTED_CRUISE"
    ABSORBING_PRESSURE = "ABSORBING_PRESSURE"
    PARTIAL_SYNCHRONIZATION = "PARTIAL_SYNCHRONIZATION"
    COLLECTIVE_EXECUTION = "COLLECTIVE_EXECUTION"
    REFLEXIVE_CASCADE = "REFLEXIVE_CASCADE"
    POST_RELEASE_REBALANCE = "POST_RELEASE_REBALANCE"


EXECUTION_TYPE_LABELS = {
    ExecutionType.TYPE_I: "Distributed Execution",
    ExecutionType.TYPE_II: "Collective Execution",
    ExecutionType.TYPE_III: "Reflexive Collective Execution",
}

REGIME_S_C_MAP = [
    (0.00, 0.30, [RegimeLabel.DISTRIBUTED_CRUISE, RegimeLabel.ABSORBING_PRESSURE]),
    (0.30, 0.65, [RegimeLabel.PARTIAL_SYNCHRONIZATION]),
    (0.65, 1.00, [RegimeLabel.COLLECTIVE_EXECUTION, RegimeLabel.REFLEXIVE_CASCADE]),
]


@dataclass
class ExecutionAuthorizationEvent:
    event_authorized: bool = False
    event_type: str = "unknown"
    event_proximity_minutes: float = float("inf")
    authorization_confidence: float = 0.0


@dataclass
class SynchronizationResult:
    synchronization_coefficient: float = 0.0
    execution_type: str = "Type I"
    execution_type_label: str = "Distributed Execution"
    regime_label: str = "DISTRIBUTED_CRUISE"
    event_authorized: bool = False
    event_authorization_confidence: float = 0.0
    absorption_capacity: float = 1.0
    valve_saturation_score: float = 0.0
    queue_pressure: float = 0.0
    hidden_flow_suspected: bool = False
    observed_dom_confidence: float = 1.0
    collective_execution_risk: float = 0.0
    reflexive_cascade_risk: float = 0.0

    # Diagnostic notes
    diagnostics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "synchronization_coefficient": round(self.synchronization_coefficient, 4),
            "execution_type": self.execution_type,
            "execution_type_label": self.execution_type_label,
            "regime_label": self.regime_label,
            "event_authorized": self.event_authorized,
            "event_authorization_confidence": round(
                self.event_authorization_confidence, 4
            ),
            "absorption_capacity": round(self.absorption_capacity, 4),
            "valve_saturation_score": round(self.valve_saturation_score, 4),
            "queue_pressure": round(self.queue_pressure, 4),
            "hidden_flow_suspected": self.hidden_flow_suspected,
            "observed_dom_confidence": round(self.observed_dom_confidence, 4),
            "collective_execution_risk": round(self.collective_execution_risk, 4),
            "reflexive_cascade_risk": round(self.reflexive_cascade_risk, 4),
            "diagnostics": self.diagnostics,
        }


def _normalize(
    value: float, baseline: float, scale: float, max_clamp: float = 2.0
) -> float:
    if scale == 0 or baseline == 0:
        return 0.0
    ratio = abs(value - baseline) / scale
    return min(ratio / max_clamp, 1.0)


def _detect_regime(
    sc: float, reflexive: bool, absorbing: bool, post_release: bool
) -> str:
    if post_release:
        return RegimeLabel.POST_RELEASE_REBALANCE.value
    if reflexive:
        return RegimeLabel.REFLEXIVE_CASCADE.value
    if sc >= 0.65:
        return RegimeLabel.COLLECTIVE_EXECUTION.value
    if sc >= 0.30:
        return RegimeLabel.PARTIAL_SYNCHRONIZATION.value
    if absorbing:
        return RegimeLabel.ABSORBING_PRESSURE.value
    return RegimeLabel.DISTRIBUTED_CRUISE.value


def _compute_absorption(
    valve_saturation: float, sc: float, cvd_trend_strong: bool
) -> Tuple[float, bool]:
    raw_capacity = max(0.0, 1.0 - valve_saturation)
    if cvd_trend_strong and sc < 0.3:
        return raw_capacity * 0.8, True
    return raw_capacity, False


def compute_synchronization(
    price_displacement: float = 0.0,
    cvd_acceleration: float = 0.0,
    volume_spike_ratio: float = 1.0,
    spread_widening_ratio: float = 0.0,
    volatility_expansion: float = 0.0,
    event_proximity_minutes: float = float("inf"),
    prior_cruise_deviation: float = 0.0,
    cvd_trend_strong: bool = False,
    price_bounded_while_cvd_trends: bool = False,
    event_type: str = "unknown",
    force_post_release: bool = False,
) -> SynchronizationResult:
    baseline_volume = 1.0
    volume_factor = _normalize(volume_spike_ratio, baseline_volume, baseline_volume)

    baseline_spread = 0.01
    if spread_widening_ratio <= baseline_spread:
        spread_factor = 0.0
    else:
        spread_factor = _normalize(
            spread_widening_ratio, baseline_spread, baseline_spread * 5
        )

    price_factor = min(abs(price_displacement) / 3.0, 1.0)

    cvd_factor = min(abs(cvd_acceleration) / 2.0, 1.0)

    vol_factor = min(volatility_expansion / 2.0, 1.0)

    event_factor = 0.0
    if event_proximity_minutes < 60:
        event_factor = max(0.0, 1.0 - event_proximity_minutes / 60.0)

    cruise_deviation_factor = min(prior_cruise_deviation / 2.0, 1.0)

    weights = {
        "price": 0.25,
        "cvd": 0.20,
        "volume": 0.15,
        "spread": 0.10,
        "volatility": 0.10,
        "event": 0.10,
        "cruise_deviation": 0.10,
    }

    sc = (
        weights["price"] * price_factor
        + weights["cvd"] * cvd_factor
        + weights["volume"] * volume_factor
        + weights["spread"] * spread_factor
        + weights["volatility"] * vol_factor
        + weights["event"] * event_factor
        + weights["cruise_deviation"] * cruise_deviation_factor
    )

    sc = max(0.0, min(1.0, sc))

    valve_saturation = volume_factor * 0.4 + price_factor * 0.3 + cvd_factor * 0.3
    valve_saturation = max(0.0, min(1.0, valve_saturation))

    absorption_capacity, hidden_flow = _compute_absorption(
        valve_saturation, sc, cvd_trend_strong
    )

    if price_bounded_while_cvd_trends:
        hidden_flow = True

    queue_pressure = price_factor * 0.3 + volume_factor * 0.3 + valve_saturation * 0.4
    queue_pressure = max(0.0, min(1.0, queue_pressure))

    event_authorized = event_proximity_minutes < 60 and event_type != "unknown"
    auth_confidence = event_factor if event_authorized else 0.0

    reflexive = sc >= 0.65 and queue_pressure > 0.6 and vol_factor > 0.5
    collective_risk = sc * 0.7 + queue_pressure * 0.3
    collective_risk = max(0.0, min(1.0, collective_risk))

    cascade_risk = 0.0
    if reflexive:
        cascade_risk = min(1.0, collective_risk * 1.2 * vol_factor)
    else:
        cascade_risk = collective_risk * 0.2

    if reflexive:
        exec_type = ExecutionType.TYPE_III
    elif sc >= 0.30:
        exec_type = ExecutionType.TYPE_II
    else:
        exec_type = ExecutionType.TYPE_I

    regime = _detect_regime(sc, reflexive, hidden_flow, force_post_release)

    observed_dom_confidence = max(0.0, 1.0 - queue_pressure * 0.5)

    diagnostics = _generate_diagnostics(
        price_displacement,
        cvd_acceleration,
        sc,
        regime,
        hidden_flow,
        event_authorized,
        valve_saturation,
        price_bounded_while_cvd_trends,
        force_post_release,
    )

    return SynchronizationResult(
        synchronization_coefficient=sc,
        execution_type=exec_type.value,
        execution_type_label=EXECUTION_TYPE_LABELS[exec_type],
        regime_label=regime,
        event_authorized=event_authorized,
        event_authorization_confidence=auth_confidence,
        absorption_capacity=absorption_capacity,
        valve_saturation_score=valve_saturation,
        queue_pressure=queue_pressure,
        hidden_flow_suspected=hidden_flow,
        observed_dom_confidence=observed_dom_confidence,
        collective_execution_risk=collective_risk,
        reflexive_cascade_risk=cascade_risk,
        diagnostics=diagnostics,
    )


def _generate_diagnostics(
    price_displacement: float,
    cvd_acceleration: float,
    sc: float,
    regime: str,
    hidden_flow: bool,
    event_authorized: bool,
    valve_saturation: float,
    price_bounded_while_cvd_trends: bool,
    force_post_release: bool,
) -> List[str]:
    notes = []
    if abs(cvd_acceleration) > 1.0 and abs(price_displacement) < 0.5:
        notes.append(
            "Price lagged CVD — pressure may have accumulated before price moved."
        )
    if hidden_flow and not force_post_release:
        notes.append(
            "Pressure was absorbed before rupture — CVD trended while price was contained."
        )
    if event_authorized:
        notes.append(
            "Event appears to have synchronized participants — authorization signal detected."
        )
    if sc < 0.3 and regime == RegimeLabel.DISTRIBUTED_CRUISE.value:
        notes.append(
            "Movement looks like ordinary trend — no synchronization detected."
        )
    elif sc >= 0.65:
        notes.append(
            "Movement resembles pressure release — collective or reflexive execution."
        )
    if force_post_release:
        notes.append("Post-event bounce suggests valve reopening / rebalancing phase.")
    if valve_saturation > 0.7:
        notes.append("Valve saturation high — absorption capacity nearing limit.")
    if price_bounded_while_cvd_trends:
        notes.append(
            "CVD trends strongly while price remains bounded — possible absorption phase."
        )
    return notes


def estimate_price_displacement(prices: List[float]) -> float:
    if len(prices) < 2:
        return 0.0
    return prices[-1] - prices[-2]


def estimate_volume_spike_ratio(volumes: List[float]) -> float:
    if len(volumes) < 2:
        return 1.0
    recent = volumes[-1]
    avg = sum(volumes[:-1]) / len(volumes[:-1])
    if avg == 0:
        return 1.0
    return recent / avg


def estimate_spread_widening(candle: dict, avg_range: float) -> float:
    high = candle.get("high", 0)
    low = candle.get("low", 0)
    current_range = high - low
    if avg_range == 0:
        return 0.0
    return current_range / avg_range


def estimate_volatility_expansion(current_iv_delta: float, iv_std: float) -> float:
    if iv_std == 0:
        return 0.0
    return abs(current_iv_delta) / iv_std
