Upgrade Aerotrader with Collective Execution / Synchronization modeling.

Goal:
Add a market-state layer that distinguishes ordinary flow from synchronized execution events, using the recent SPY/FOMC pressure-release example as the conceptual reference.

Core concepts to implement:

1. Synchronization Coefficient (S_c)
Definition:
Degree to which independent participants appear to be acting in temporal alignment.

Suggested inputs:
- abrupt price displacement
- CVD acceleration
- volume spike
- spread widening
- volatility expansion
- proximity to known event timestamps
- deviation from prior cruise-mode behavior

Output:
S_c in range 0.0–1.0

Interpretation:
0.0–0.30 = DISPERSED_FLOW
0.30–0.65 = PARTIAL_ALIGNMENT
0.65–1.00 = COLLECTIVE_EXECUTION

2. Execution Type Classification

Type I — Distributed Execution
Normal dispersed order flow.
Price and CVD move gradually.
System remains in cruise/absorption mode.

Type II — Collective Execution
Shared trigger causes simultaneous participant action.
Examples: FOMC, CPI, earnings, major gamma level break.
Visible as sharp price displacement + CVD impulse + volume surge.

Type III — Reflexive Collective Execution
Execution causes further execution.
Participants begin reacting to the market reacting.
Examples: stop cascades, dealer hedging feedback, volatility breakout, momentum algo pile-on.

3. Event Authorization Layer

Add concept:
Execution Authorization Event (E_a)

Definition:
A catalyst that permits or unlocks pressure that may already have been latent.

Important:
Do not assume event creates pressure.
Model event as possible synchronization trigger.

Fields:
- event_authorized: bool
- event_type: macro / earnings / technical / gamma / unknown
- event_proximity_minutes
- authorization_confidence

4. Cruise Mode Upgrade

Current cruise mode should not mean inactivity.

Update interpretation:
Cruise mode = pressure being successfully absorbed/metabolized.

Add fields:
- absorption_capacity
- valve_saturation_score
- queue_pressure
- hidden_flow_suspected
- observed_dom_confidence

Useful rule:
If CVD trends strongly while price remains bounded, mark as possible absorption phase.

5. Output Schema Additions

Add to JSON/CSV/MD/HTML outputs:

synchronization_coefficient
execution_type
execution_type_label
event_authorized
event_authorization_confidence
valve_saturation_score
queue_pressure
hidden_flow_suspected
observed_dom_confidence
collective_execution_risk
reflexive_cascade_risk

6. Suggested Regime Labels

DISTRIBUTED_CRUISE
ABSORBING_PRESSURE
PARTIAL_SYNCHRONIZATION
COLLECTIVE_EXECUTION
REFLEXIVE_CASCADE
POST_RELEASE_REBALANCE

7. Diagnostic Notes

Generated reports should explain whether:
- price lagged CVD
- pressure was absorbed before rupture
- event appeared to synchronize participants
- movement looked like ordinary trend or pressure release
- post-event bounce suggests valve reopening / rebalancing

Reference phrase:
Observed DOM ≠ Actual DOM

Treat DOM/visual order-book tools as sensors, not ground truth.

8. Optional 2D Crow Simulator Bridge

Since the crow sim is being upgraded too, mirror the same logic:

Crow flock model:
Type I = scattered foraging / distributed movement
Type II = flock lands/takes off together after scout signal
Type III = panic cascade / recursive flock reaction

Crow fields:
- flock_synchronization
- scout_alert_active
- collective_takeoff_risk
- landing_convergence_score
- roost_pressure
- disturbance_proximity

The scout crow is equivalent to an authorization/synchronization signal:
one agent detects a threat, emits alert, flock state transitions collectively.

Deliverables:
- New module for synchronization/execution classification
- Tests for Type I, Type II, Type III
- Updated reports and dashboard labels
- Backward-compatible schema additions
