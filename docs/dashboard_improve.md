Yes. The important change is to make this a **runtime control plane**, not just a UI form. The dashboard should be able to start/stop the agent and safely change configuration, while the trading engine remains authoritative.

Use this directly with Claude Code:

# Add Dashboard Agent Controls & Runtime Configuration

I want to change the existing trading-agent application so that the **dashboard becomes the control center for the autonomous agent**.

The user should be able to:

1. Start the trading agent from the dashboard
2. Stop/pause the trading agent from the dashboard
3. See whether the agent is currently running
4. Change the agent's trading parameters from the dashboard
5. See the currently active configuration
6. Apply configuration changes safely
7. See when the configuration was last changed
8. Understand exactly what the agent is currently doing

This must integrate with the existing architecture.

**Do not rewrite working trading logic.**

---

# 1. Core Concept

Currently the agent is likely started manually from the terminal/configuration.

Change the architecture so that the dashboard controls an **Agent Runtime**.

Conceptually:

```text
                    DASHBOARD
                        │
              ┌─────────┴─────────┐
              │                   │
           START/STOP        CONFIGURATION
              │                   │
              └─────────┬─────────┘
                        ▼
                 AGENT CONTROLLER
                        │
                        ▼
                 AUTONOMOUS LOOP
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       STRATEGY        AI           RISK
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                    EXECUTION
                        │
                        ▼
                     ALPACA
```

The dashboard should **control** the agent but should not contain trading logic.

---

# 2. Important Safety Principle

The dashboard must NEVER bypass the existing:

```text
Risk Engine
```

The control flow must remain:

```text
Dashboard
    ↓
Agent Controller
    ↓
Strategy
    ↓
AI
    ↓
Risk Engine
    ↓
Execution
    ↓
Alpaca
```

The dashboard can modify configuration.

It cannot directly submit trades.

---

# 3. Agent Lifecycle

Create an explicit agent lifecycle.

The agent should have states such as:

```text
STOPPED
STARTING
RUNNING
PAUSED
STOPPING
ERROR
```

Use a clear state machine rather than a simple boolean if practical.

Example:

```text
STOPPED
   │
   │ START
   ▼
STARTING
   │
   ▼
RUNNING
   │
   │ PAUSE
   ▼
PAUSED
   │
   │ RESUME
   ▼
RUNNING
   │
   │ STOP
   ▼
STOPPING
   │
   ▼
STOPPED
```

If something fails:

```text
RUNNING
   ↓
ERROR
```

The dashboard must clearly communicate the current state.

---

# 4. Dashboard Agent Control Panel

Add a prominent control area to the dashboard.

Example:

```text
┌─────────────────────────────────────────────┐
│ AGENT CONTROL                               │
│                                             │
│ ● RUNNING                                   │
│                                             │
│ Started: 09:32:14                           │
│ Last heartbeat: 2 seconds ago               │
│ Current strategy: Momentum + Volatility     │
│                                             │
│ [ PAUSE ]        [ STOP AGENT ]             │
└─────────────────────────────────────────────┘
```

When stopped:

```text
┌─────────────────────────────────────────────┐
│ AGENT CONTROL                               │
│                                             │
│ ○ STOPPED                                   │
│                                             │
│ Current strategy: Momentum + Volatility     │
│                                             │
│ [ START AGENT ]                             │
└─────────────────────────────────────────────┘
```

Use a confirmation dialog before stopping an actively trading agent.

---

# 5. Starting the Agent

When the user clicks:

```text
START AGENT
```

the dashboard should call the backend.

The backend should:

1. Validate the current configuration
2. Verify Alpaca connectivity
3. Verify market-data availability
4. Verify the risk engine is healthy
5. Verify required AI configuration exists
6. Start the agent loop
7. Record the start event
8. Return the new agent state

Do not start the agent if critical dependencies are unavailable.

Return a useful error instead.

Example:

```text
Cannot start agent.

Reason:
Alpaca market-data connection unavailable.
```

---

# 6. Stopping the Agent

When the user clicks:

```text
STOP AGENT
```

the agent should:

1. Stop generating new trade signals
2. Stop submitting new orders
3. Finish any currently executing order safely
4. Continue handling already-open positions according to the configured policy
5. Update state to STOPPED
6. Record the event

**Do not automatically liquidate all positions simply because the agent is stopped.**

Position liquidation should be a separate explicit action.

If the existing architecture has different semantics, preserve the safest existing behavior.

---

# 7. Pause vs Stop

If practical, support both:

### PAUSE

The agent:

- stops opening new positions
- continues monitoring existing positions
- continues risk monitoring
- can resume later

### STOP

The autonomous trading loop shuts down.

Existing positions remain visible and manageable according to the existing position-management logic.

If implementing both would create unnecessary complexity, implement **STOP + START first** and add PAUSE only if it is trivial.

---

# 8. Runtime Configuration

Add a dashboard section called:

```text
AGENT CONFIGURATION
```

The user should be able to modify important strategy/risk parameters without editing `.env` or source code.

Organize settings into categories.

---

# 9. Strategy Parameters

Example:

```text
STRATEGY

Strategy
[ Momentum + Volatility ▼ ]

Minimum Signal Confidence
[ 0.70 ]

Minimum Expected Edge
[ 0.05 ]

Lookback Period
[ 20 ]

Momentum Threshold
[ 1.5 ]

Volatility Threshold
[ 0.20 ]

Scan Interval
[ 60 seconds ]
```

Only expose parameters that the existing strategy actually supports.

**Do not invent settings that have no effect.**

Every dashboard control must map to a real backend configuration value.

---

# 10. Options Parameters

Create an options section.

Potential configurable values:

```text
OPTIONS

Minimum Volume
[ ... ]

Minimum Open Interest
[ ... ]

Maximum Bid/Ask Spread
[ ... ]

Minimum Days to Expiration
[ ... ]

Maximum Days to Expiration
[ ... ]

Target Delta
[ ... ]

Maximum Allowed IV
[ ... ]
```

Only implement parameters that are actually used by the current strategy/risk engine.

---

# 11. Risk Parameters

This section is especially important.

Example:

```text
RISK LIMITS

Max Risk / Trade
[ 1.0% ]

Max Portfolio Exposure
[ 40% ]

Max Open Positions
[ 5 ]

Max Daily Loss
[ 3.0% ]

Max Drawdown
[ 10% ]

Max Underlying Concentration
[ 20% ]
```

These values must be enforced by the deterministic risk engine.

The AI cannot override them.

---

# 12. AI Parameters

Create an AI section where appropriate.

Example:

```text
AI

AI Supervisor
[ ON ]

Minimum AI Confidence
[ 0.70 ]

Require AI Approval
[ ON ]

Model
[ Claude ]

Temperature
[ 0.2 ]
```

Do not expose unnecessary model parameters.

The important controls are:

- whether AI supervision is enabled
- minimum confidence
- whether AI approval is required

The AI still cannot bypass the risk engine.

---

# 13. Execution Parameters

If supported by the current execution engine:

```text
EXECUTION

Order Type
[ Market / Limit ]

Max Slippage
[ ... ]

Max Order Value
[ ... ]

Duplicate Order Protection
[ ON ]
```

Do not expose dangerous execution controls unless they already have proper validation.

---

# 14. Configuration Validation

Never allow arbitrary values to reach the trading engine.

Create a configuration model such as:

```python
AgentConfig
```

Validate:

- types
- minimums
- maximums
- relationships between settings

Examples:

```text
max_risk_per_trade > 0
max_risk_per_trade < max_portfolio_exposure
max_positions >= 1
max_daily_loss > 0
```

Reject invalid configurations before applying them.

Example:

```text
Configuration rejected.

Max risk per trade cannot exceed
maximum portfolio exposure.
```

---

# 15. Applying Configuration Changes

Do NOT silently change parameters while the agent is actively executing a trade.

Use:

```text
EDIT
  ↓
VALIDATE
  ↓
REVIEW CHANGES
  ↓
APPLY
```

For example:

```text
CONFIGURATION CHANGES

Max Risk / Trade
1.0% → 0.5%

Max Positions
5 → 3

AI Confidence
0.70 → 0.80

[ CANCEL ]        [ APPLY CHANGES ]
```

After applying:

```text
✓ Configuration updated

Applied at:
09:51:42

Next agent cycle will use the new configuration.
```

---

# 16. Runtime Configuration Rules

Prefer applying configuration changes at the **next agent cycle** rather than abruptly mutating state in the middle of a decision.

If the agent is currently:

```text
ANALYZING
```

do not change the configuration halfway through the analysis.

Finish the current cycle.

Then apply the new configuration.

This prevents inconsistent decisions.

---

# 17. Configuration Persistence

Store the active configuration in SQLite.

Do not rely exclusively on Streamlit session state.

The configuration should survive:

- dashboard refresh
- backend restart where appropriate
- Streamlit restart

Store:

```text
config_id
created_at
updated_at
parameter values
active
```

Keep a lightweight configuration history.

---

# 18. Configuration History

Add a small history section:

```text
CONFIGURATION HISTORY

09:51
Risk / Trade: 1.0% → 0.5%
Max Positions: 5 → 3
Changed by: Dashboard

09:21
AI Confidence: 0.65 → 0.70
Changed by: Dashboard
```

This is useful for debugging and the hackathon demo.

---

# 19. Agent Runtime API

Create backend endpoints such as:

```text
GET  /api/agent/status

POST /api/agent/start

POST /api/agent/stop

POST /api/agent/pause

POST /api/agent/resume

GET  /api/agent/config

PUT  /api/agent/config

GET  /api/agent/config/history
```

Only implement pause/resume if practical.

The exact API structure can follow the existing backend conventions.

---

# 20. Agent Controller

Create a central:

```text
AgentController
```

responsible for:

- lifecycle
- runtime state
- starting
- stopping
- pausing
- configuration changes
- health
- heartbeat

Conceptually:

```python
class AgentController:
    start()
    stop()
    pause()
    resume()
    get_status()
    get_config()
    update_config()
```

Do not put the actual strategy logic here.

The controller manages the runtime.

---

# 21. Single Agent Instance

Prevent multiple agent loops from accidentally running simultaneously.

For example, clicking:

```text
START AGENT
```

twice must NOT create:

```text
Agent Loop #1
Agent Loop #2
```

There must only ever be one active trading loop.

If already running:

```text
Agent is already running.
```

---

# 22. Heartbeat

The agent should expose:

```text
last_heartbeat
```

Update it every successful loop cycle.

Dashboard:

```text
AGENT
● RUNNING

Last heartbeat:
2 seconds ago
```

If the heartbeat becomes stale:

```text
⚠ AGENT MAY BE UNRESPONSIVE
```

Do not claim the agent is healthy if it has stopped updating.

---

# 23. Current Activity

The dashboard should display what the agent is currently doing.

Example:

```text
CURRENT ACTIVITY

● SCANNING MARKET

Universe:
SPY
QQQ
NVDA
AAPL
TSLA

Last scan:
09:52:31

Candidates:
3

AI evaluations:
1

Next scan:
09:53:00
```

Possible states:

```text
STARTING
SCANNING
CALCULATING FEATURES
GENERATING SIGNALS
EVALUATING WITH AI
RISK CHECK
EXECUTING
MONITORING POSITIONS
IDLE
STOPPING
ERROR
```

---

# 24. Dashboard Layout

Update the Overview page so the agent control is highly visible.

Recommended layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ ALPHA — AUTONOMOUS OPTIONS AGENT             PAPER TRADING   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  AGENT STATUS                                                │
│  ● RUNNING                       [PAUSE] [STOP]              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Portfolio      Today's P&L      Total P&L       Drawdown     │
│ $102,481       +$842            +$2,481         -1.8%        │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ CURRENT ACTIVITY                 ACTIVE POSITIONS             │
│                                                              │
│ Scanning NVDA                   NVDA 180C       +$184        │
│ Candidates: 3                   SPY 580P        -$32         │
│ AI evaluations: 1               QQQ 490C        +$91         │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ AGENT ACTIVITY / DECISION JOURNAL                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Add a dedicated:

```text
Agent
```

page containing:

- lifecycle controls
- configuration
- current activity
- heartbeat
- configuration history
- recent decisions

---

# 25. Configuration UX

Use sensible input controls:

### Numeric parameters

Use:

- number inputs
- sliders where appropriate

### Boolean parameters

Use:

- toggles

### Strategy selection

Use:

- select/dropdown

### Risk levels

Use:

- numeric input with clear units

Always display units.

For example:

```text
Max Risk / Trade
[ 1.0 ] %
```

rather than:

```text
[ 0.01 ]
```

where possible.

---

# 26. Important: Percentages

Be extremely careful with percentage conversion.

The UI might show:

```text
1.0%
```

while the backend stores:

```text
0.01
```

Implement conversion explicitly and test it.

Do not accidentally turn:

```text
1%
```

into:

```text
100%
```

---

# 27. Start Configuration Review

When starting the agent, show the configuration being used.

Example:

```text
START AGENT

Strategy:
Momentum + Volatility

Risk / Trade:
0.5%

Max Positions:
3

AI Supervisor:
ON

AI Confidence:
80%

Scan Interval:
60s

Environment:
PAPER TRADING

[ CANCEL ]      [ START AGENT ]
```

This makes the system much easier to understand during the demo.

---

# 28. Stop Confirmation

When stopping:

```text
STOP AGENT?

The agent will stop opening new positions.

Existing positions will remain open
and continue to be handled according to
the position-management policy.

[ CANCEL ]      [ STOP AGENT ]
```

Do not make this unnecessarily scary or complicated.

---

# 29. Error Handling

If starting fails:

```text
AGENT FAILED TO START

Reason:
Alpaca connection unavailable.

No trades were submitted.

[ RETRY ]
```

If configuration update fails:

```text
CONFIGURATION NOT APPLIED

Reason:
Max risk per trade must be below
maximum portfolio exposure.

No settings were changed.
```

Never leave the UI showing an old state as if the update succeeded.

---

# 30. Security / Safety

The dashboard must NOT expose:

- Alpaca API key
- Alpaca secret
- Claude API key
- environment secrets

The dashboard should never directly access secrets.

All sensitive configuration remains server-side.

---

# 31. Tests

Add tests for:

### Agent lifecycle

- start
- duplicate start
- stop
- pause
- resume
- error state

### Configuration

- valid configuration
- invalid configuration
- persistence
- update
- history

### Safety

- configuration cannot bypass risk engine
- agent cannot create duplicate loops
- stop prevents new orders
- invalid configuration cannot reach strategy

### API

Test:

```text
GET /api/agent/status
POST /api/agent/start
POST /api/agent/stop
GET /api/agent/config
PUT /api/agent/config
```

---

# 32. Important: Do Not Fake Runtime State

Do not make the dashboard say:

```text
RUNNING
```

just because the user clicked a button.

The backend must actually start the agent loop.

Likewise:

```text
STOPPED
```

must reflect the actual runtime state.

The dashboard is a representation of the backend state, not the source of truth.

---

# 33. Do Not Duplicate Trading Logic

The dashboard must NOT contain code such as:

```python
if price > moving_average:
    buy()
```

or:

```python
if confidence > 0.8:
    submit_order()
```

The dashboard only does:

```text
User Input
↓
Backend API
↓
Agent Controller
↓
Trading System
```

All trading decisions remain in the backend.

---

# 34. Preserve Existing Functionality

Before making changes:

1. Inspect the current application.
2. Understand how the agent is currently started.
3. Understand how configuration currently works.
4. Understand how the trading loop currently works.
5. Understand how the dashboard currently gets data.

Then integrate the new control plane into the existing architecture.

Do not rewrite working components unnecessarily.

---

# 35. Implementation Priority

Implement in this order:

## Priority 1

Agent status endpoint.

## Priority 2

Agent Controller.

## Priority 3

Start/stop functionality.

## Priority 4

Runtime configuration model.

## Priority 5

Configuration API.

## Priority 6

Dashboard controls.

## Priority 7

Configuration persistence/history.

## Priority 8

Current activity/heartbeat.

## Priority 9

Pause/resume if practical.

## Priority 10

Visual polish.

---

# 36. Definition of Done

The feature is complete when:

- [ ] Dashboard shows real agent state
- [ ] User can start agent from dashboard
- [ ] User can stop agent from dashboard
- [ ] Duplicate agent loops are impossible
- [ ] Agent heartbeat is visible
- [ ] Current activity is visible
- [ ] User can change supported parameters
- [ ] Configuration is validated
- [ ] Configuration persists
- [ ] Configuration history is recorded
- [ ] Configuration changes do not bypass risk controls
- [ ] Start/stop events are logged
- [ ] Dashboard never directly submits orders
- [ ] Paper trading status is clearly visible
- [ ] Tests pass
- [ ] Existing trading functionality still works

---

# 37. START NOW

Do not immediately rewrite the application.

First inspect the repository and answer:

```text
1. How is the agent currently started?
2. Where does the autonomous loop live?
3. Where are current strategy parameters stored?
4. Where are risk parameters stored?
5. How does the dashboard communicate with the backend?
6. Is there already an agent state model?
7. What is the minimum architecture change required?
```

Then implement **Priority 1–3 first**:

```text
AGENT STATUS
     ↓
AGENT CONTROLLER
     ↓
START / STOP
```

Verify that the dashboard can genuinely start and stop the real agent.

Only after that works should you implement runtime configuration.

At the end of each implementation stage, report:

```text
AGENT CONTROL STATUS
--------------------

Implemented:
- ...

Agent lifecycle:
- ...

API endpoints:
- ...

Configuration:
- ...

Tests:
- ...

Verified manually:
- ...

Known issues:
- ...

Next step:
- ...
```

Remember:

**The dashboard is the control plane.
The backend is the source of truth.
The risk engine remains the final authority.**
