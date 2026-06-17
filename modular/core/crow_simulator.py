from dataclasses import dataclass, field
from typing import List, Optional, Dict

from .synchronization import (
    compute_synchronization,
    SynchronizationResult,
    RegimeLabel,
    EXECUTION_TYPE_LABELS,
    ExecutionType,
)


class FlockExecutionType:
    SCATTERED_FORAGING = "Type I — Scattered Foraging"
    SYNCHRONIZED_MOVEMENT = "Type II — Flock Synchronized Movement"
    PANIC_CASCADE = "Type III — Panic Cascade"


FLOCK_EXECUTION_MAP = {
    ExecutionType.TYPE_I: FlockExecutionType.SCATTERED_FORAGING,
    ExecutionType.TYPE_II: FlockExecutionType.SYNCHRONIZED_MOVEMENT,
    ExecutionType.TYPE_III: FlockExecutionType.PANIC_CASCADE,
}


@dataclass
class CrowFlockState:
    flock_synchronization: float = 0.0
    scout_alert_active: bool = False
    collective_takeoff_risk: float = 0.0
    landing_convergence_score: float = 1.0
    roost_pressure: float = 0.0
    disturbance_proximity: float = float("inf")
    flock_execution_type: str = FlockExecutionType.SCATTERED_FORAGING
    regime_label: str = RegimeLabel.DISTRIBUTED_CRUISE.value
    diagnostics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "flock_synchronization": round(self.flock_synchronization, 4),
            "scout_alert_active": self.scout_alert_active,
            "collective_takeoff_risk": round(self.collective_takeoff_risk, 4),
            "landing_convergence_score": round(self.landing_convergence_score, 4),
            "roost_pressure": round(self.roost_pressure, 4),
            "disturbance_proximity": round(self.disturbance_proximity, 4),
            "flock_execution_type": self.flock_execution_type,
            "regime_label": self.regime_label,
            "diagnostics": self.diagnostics,
        }


def compute_flock_state(market_sync: SynchronizationResult) -> CrowFlockState:
    sc = market_sync.synchronization_coefficient
    queue_pressure = market_sync.queue_pressure
    cascade_risk = market_sync.reflexive_cascade_risk
    event_auth = market_sync.event_authorized
    regime = market_sync.regime_label

    flock_sync = sc
    scout_active = event_auth
    roost_pressure = queue_pressure

    if cascade_risk > 0.5:
        collective_takeoff_risk = min(1.0, cascade_risk * 1.1)
    else:
        collective_takeoff_risk = sc * 0.5

    landing_convergence = max(0.0, 1.0 - queue_pressure)

    market_exec_type = market_sync.execution_type
    for et in ExecutionType:
        if et.value == market_exec_type:
            flock_type = FLOCK_EXECUTION_MAP[et]
            break
    else:
        flock_type = FlockExecutionType.SCATTERED_FORAGING

    dist_prox = float("inf")
    if not scout_active:
        pass
    elif sc < 0.3:
        dist_prox = 30.0
    elif sc < 0.65:
        dist_prox = 10.0
    else:
        dist_prox = 2.0

    diagnostics = _crow_diagnostics(flock_sync, scout_active, regime, roost_pressure)

    return CrowFlockState(
        flock_synchronization=flock_sync,
        scout_alert_active=scout_active,
        collective_takeoff_risk=collective_takeoff_risk,
        landing_convergence_score=landing_convergence,
        roost_pressure=roost_pressure,
        disturbance_proximity=dist_prox,
        flock_execution_type=flock_type,
        regime_label=regime,
        diagnostics=diagnostics,
    )


def _crow_diagnostics(
    flock_sync: float,
    scout_alert: bool,
    regime: str,
    roost_pressure: float,
) -> List[str]:
    notes = []
    if scout_alert:
        notes.append("Scout crow detected disturbance — flock may align.")
    if flock_sync < 0.3:
        notes.append("Flock is scattered foraging — no collective behavior.")
    elif flock_sync < 0.65:
        notes.append(
            "Flock showing partial alignment — potential coordinated movement."
        )
    else:
        notes.append(
            "Flock in synchronized state — collective takeoff or landing imminent."
        )
    if roost_pressure > 0.7:
        notes.append("Roost pressure high — flock ready to disperse on next signal.")
    return notes
