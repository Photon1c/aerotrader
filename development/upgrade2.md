I would now rewrite Aerotrader regime language.

Legacy model (older)
TAKEOFF
CRUISE
LANDING
STALL
TURBULENCE
Better model (new)
STABLE_CRUISE
PRESSURE_ACCUMULATION
STEP_CLIMB
STEP_DESCENT
ALTITUDE_TRANSITION
COLLECTIVE_EXECUTION_MANEUVER
REFLEXIVE_CASCADE
FAILED_RESTORATION
FLIGHT_LEVEL_STABILIZATION
PERSISTENCE_DECAY

Cleaner.

Much more precise.

I would formally define these.

Step Climb Event

An upward flight-level transition initiated by synchronized
collective execution causing price to leave its existing
cruise band and establish a higher equilibrium zone.
Step Descent Event

A downward flight-level transition initiated by synchronized
collective execution causing price to leave its existing
cruise band and establish a lower equilibrium zone.
Flight-Level Stabilization

The process by which price establishes a new equilibrium zone
following a collective execution maneuver.
Altitude Transition

Temporary regime in which price is actively moving between
stable operating bands.
