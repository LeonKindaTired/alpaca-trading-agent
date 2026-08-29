# Alpaca AI Trading Agent — Hackathon Build Plan

You are the lead engineer building an autonomous AI options-trading agent for the **Alpaca AI Trading Agent Hackathon**.

The objective is not to build a production-grade trading platform.

The objective is to build the **strongest, most defensible autonomous trading agent possible within a limited hackathon window**.

The agent must:

- Analyze live US market/options data
- Identify potential options opportunities
- Use quantitative signals to generate candidate trades
- Use an AI reasoning layer where it provides genuine value
- Apply deterministic risk controls
- Execute paper trades through Alpaca
- Autonomously manage open positions
- Log every decision and trade
- Demonstrate measurable performance during the competition
- Clearly explain _why_ it made each decision

---

# 1. Core Architecture

Use this architecture:

```text
                    LIVE MARKET DATA
                          │
                          ▼
                 ┌─────────────────┐
                 │ Feature Engine  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Strategy Engine │
                 └────────┬────────┘
                          │
                          ▼
                Candidate Opportunities
                          │
                          ▼
                 ┌─────────────────┐
                 │   AI Supervisor │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │   RISK ENGINE   │◄──── Portfolio State
                 └────────┬────────┘
                          │
                     APPROVED?
                       /     \
                     NO       YES
                     │         │
                     ▼         ▼
                   REJECT   EXECUTION
                               │
                               ▼
                          ALPACA PAPER
                               │
                               ▼
                       POSITION MANAGER
                               │
                               ▼
                        DECISION JOURNAL
```

## Non-negotiable rule

**The LLM never has direct authority to place an order.**

The AI can recommend:

- BUY
- SELL
- HOLD
- contract
- confidence
- thesis
- expected horizon
- risk factors
- invalidation conditions

But the deterministic risk engine has final authority.

No trade can bypass it.

---

# 2. Hackathon Priorities

Prioritize work in this order:

```text
1. Get a real Alpaca paper trade working
2. Build a robust trading/risk loop
3. Develop and validate a potentially profitable strategy
4. Add AI where it demonstrably improves decisions
5. Run the agent continuously
6. Build decision journaling
7. Build a minimal dashboard
8. Polish the demo
```

Do **not** spend significant time building infrastructure that doesn't improve these objectives.

---

# 3. Technology Stack

Use:

## Backend

- Python 3.11+
- FastAPI
- Pydantic
- asyncio
- pandas
- NumPy
- scipy

## Trading

- Alpaca Python SDK/API
- Alpaca paper trading
- Alpaca market/options data

## AI

Use **Claude** as the primary LLM.

Create only two implementations:

```text
ClaudeAI
MockAI
```

The MockAI implementation is required for testing.

Do **not** build a multi-provider AI abstraction.

Do **not** build Anthropic + OpenAI + Gemini + other provider integrations unless there is a compelling hackathon reason.

## Database

Use:

**SQLite**

Do not design a PostgreSQL migration architecture.

Keep the schema clean, but optimize for speed of implementation.

## Dashboard

Use:

**Streamlit**

The dashboard is view-only.

Do not build React, TypeScript, Vite, or a separate frontend application.

The dashboard is lower priority than the trading engine.

## Testing

Use:

- pytest
- pytest-asyncio

---

# 4. Repository Structure

Keep the repository simple:

```text
alpaca-trading-agent/
│
├── backend/
│   ├── app/
│   │   ├── config/
│   │   ├── data/
│   │   ├── features/
│   │   ├── strategies/
│   │   ├── ai/
│   │   ├── risk/
│   │   ├── execution/
│   │   ├── portfolio/
│   │   ├── backtesting/
│   │   ├── monitoring/
│   │   ├── database/
│   │   └── main.py
│   │
│   ├── tests/
│   └── scripts/
│
├── dashboard/
│   └── app.py
│
├── strategies/
│   ├── research/
│   └── configs/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── backtests/
│
├── docs/
│
├── .env.example
├── README.md
└── requirements.txt
```

Avoid unnecessary microservices.

---

# 5. HARD TIME BUDGET

Treat the following as internal deadlines.

The exact hours can be adjusted if the actual hackathon duration differs, but **do not allow architecture work to consume the competition window**.

## By Hour 4

Have:

- project initialized
- environment configuration
- Alpaca credentials working
- Alpaca account connection
- basic logging
- SQLite
- basic tests

## By Hour 8

Have:

- live market data
- options chain retrieval
- normalized internal market-data models
- basic feature calculations

## BY HOUR 12 — CRITICAL DEADLINE

The system must be capable of:

```text
Market Data
→ Signal
→ Risk Check
→ Paper Order
→ Position
```

At least one complete paper-trading cycle must work.

If this deadline is missed:

**CUT SCOPE.**

Do not respond by adding more architecture.

---

## By Hour 20

Have:

- strategy framework
- initial strategy candidates
- position sizing
- risk engine
- basic backtesting/research
- order execution
- position monitoring

## By Hour 32

Have:

- autonomous trading loop
- AI supervisor
- structured AI outputs
- decision journal
- kill switch
- automatic risk shutdowns

## Remaining Time

Prioritize:

1. paper trading
2. strategy improvement
3. AI-vs-quant evaluation
4. dashboard
5. reliability
6. demo/presentation

---

# 6. PHASE 1 — Foundation + Alpaca Integration

Do these together.

Build:

- Python environment
- `.env`
- configuration
- logging
- SQLite
- Alpaca client
- FastAPI health endpoint
- pytest setup

Create:

```text
AlpacaClient
```

Support:

## Account

- account information
- buying power
- portfolio value

## Market

- latest quotes
- historical bars

## Options

- options contracts
- options chains
- contract details

## Orders

- submit
- cancel
- retrieve
- list

## Positions

- list
- retrieve
- close

Create a MockAlpaca client for tests.

Never allow unit tests to submit real requests.

---

# 7. PHASE 2 — Market Data + Features

Create a market-data abstraction so strategies do not directly depend on Alpaca.

```text
Strategy
   ↓
MarketDataService
   ↓
Alpaca
```

Normalize market data into internal models.

For options capture, where available:

- underlying
- contract symbol
- strike
- expiration
- call/put
- bid
- ask
- last
- volume
- open interest
- implied volatility
- Greeks
- underlying price

Handle missing data explicitly.

Never silently turn missing data into zero.

---

# 8. Feature Engine

Start small.

## Underlying

Implement only features that are likely to be useful:

- returns
- realized volatility
- momentum
- moving averages
- volume changes
- ATR
- RSI

## Options

- IV
- delta
- gamma
- theta
- vega
- bid/ask spread
- volume
- open interest
- time to expiration
- distance from strike

## Regime

Implement a simple deterministic regime classifier:

```text
TRENDING_UP
TRENDING_DOWN
RANGE_BOUND
HIGH_VOLATILITY
LOW_VOLATILITY
UNKNOWN
```

Do not build a complex ML regime model initially.

---

# 9. PHASE 3 — Strategy Research

Create a strategy interface:

```python
class Strategy:
    def generate_signals(self, market_state):
        ...
```

Signals should contain:

```text
underlying
direction
confidence
thesis
expected_edge
contract
timestamp
```

Initially investigate a small number of strategies.

Potential candidates:

## A. Momentum

Trade directional moves in liquid underlyings.

## B. Volatility Mispricing

Compare implied volatility against realized volatility.

## C. Mean Reversion

Identify statistically unusual moves and potential reversions.

## D. Event/Regime-Based

Trade unusual volatility, price, or volume conditions.

---

# 10. IMPORTANT — Competition Window Research

Before committing to a strategy, determine:

- exact competition dates
- trading hours
- scoring methodology
- starting capital
- position restrictions
- available instruments
- options availability
- liquidity constraints

This research must happen **before strategy lock-in**.

Do not build an earnings-specific strategy if there are no relevant earnings/events during the competition window.

Do not build a strategy around a market event that cannot occur during the evaluation period.

The competition window determines which strategies are viable.

---

# 11. PHASE 4 — Backtesting

Do **not** pretend we have perfect historical options data if we don't.

We need to explicitly account for the historical options-data limitation.

## Default approach

Use a **synthetic options backtest** where necessary:

```text
Historical underlying prices
          ↓
Realized volatility
          ↓
Black-Scholes
          ↓
Synthetic option prices / Greeks
          ↓
Strategy backtest
```

Clearly label this as an approximation.

The backtester should allow us to test:

- directional signals
- volatility signals
- entry/exit logic
- position sizing
- risk management

But do not treat synthetic results as equivalent to real historical options execution.

The strongest validation should ultimately come from **live Alpaca paper trading**.

---

# 12. Backtest Metrics

Track:

- total P&L
- return
- Sharpe
- Sortino
- max drawdown
- win rate
- profit factor
- average trade
- number of trades
- largest win
- largest loss
- exposure

Avoid optimizing solely for historical return.

Separate:

```text
TRAIN
VALIDATION
TEST
```

where possible.

Avoid:

- look-ahead bias
- data leakage
- overfitting
- survivorship bias

---

# 13. PHASE 5 — Risk Engine

This is the most important deterministic component.

Create:

```text
RiskEngine
```

The risk engine can reject **ANY** proposed trade, including an AI-approved trade.

Implement:

## Position limits

- maximum position size
- maximum portfolio exposure
- maximum simultaneous positions
- maximum underlying concentration

## Loss limits

- maximum loss per trade
- maximum daily loss
- maximum drawdown

## Liquidity controls

- maximum bid/ask spread
- minimum volume
- minimum open interest

## Options controls

- expiration limits
- contract liquidity
- acceptable Greeks
- unacceptable spreads

Every rejection must include a reason.

Example:

```text
TRADE REJECTED

Symbol: XYZ
Reason: Bid/ask spread too wide
Spread: 11.2%
Maximum: 5%
```

---

# 14. Position Sizing

Position sizing is deterministic.

The LLM cannot decide how much capital to risk.

Base sizing on:

- account value
- maximum risk per trade
- volatility
- confidence
- portfolio exposure

Keep parameters configurable.

Example:

```text
MAX_RISK_PER_TRADE
MAX_PORTFOLIO_EXPOSURE
MAX_DAILY_LOSS
MAX_POSITIONS
```

Start conservatively and tune based on actual competition conditions.

---

# 15. PHASE 6 — AI Supervisor

Only introduce the AI after the quantitative system works.

The AI receives structured information:

```json
{
  "underlying": "...",
  "price": "...",
  "features": {},
  "signals": [],
  "options": [],
  "portfolio": {},
  "risk": {}
}
```

The AI returns strict structured output:

```json
{
  "decision": "BUY",
  "confidence": 0.82,
  "contract": "...",
  "thesis": "...",
  "expected_horizon": "...",
  "risk_factors": [],
  "invalidation_conditions": []
}
```

The output must be schema validated.

Invalid output = HOLD / reject.

---

# 16. AI Architecture

Implement and compare:

## MODE A — Quant Only

```text
Market Data
→ Features
→ Strategy
→ Risk
→ Execution
```

## MODE B — AI Supervisor

```text
Market Data
→ Features
→ Strategy
→ AI
→ Risk
→ Execution
```

Start with **Mode B** as the main system.

But retain Mode A so we can determine whether AI actually improves performance.

Do **not** build a complicated multi-agent system unless the evidence strongly suggests it is necessary.

---

# 17. AI Responsibilities

The AI should primarily provide:

## Contextual reasoning

- Does the signal make sense?
- Is the opportunity consistent with the current market regime?
- Are there conflicting signals?
- Are there obvious risks?

## Opportunity ranking

If several quantitative opportunities exist, determine which deserve attention.

## Trade explanation

Generate a concise explanation of:

- thesis
- supporting evidence
- risks
- invalidation conditions

## NOT the AI's responsibility

The AI must NOT independently determine:

- unrestricted position size
- maximum portfolio exposure
- risk limits
- whether a prohibited trade is allowed
- raw order parameters outside the validated schema

The deterministic system owns those decisions.

---

# 18. PHASE 7 — Execution Engine

Create:

```text
ExecutionEngine
```

Flow:

```text
Signal
↓
AI decision
↓
Risk validation
↓
Order construction
↓
Final validation
↓
Alpaca
↓
Execution record
```

Handle:

- order rejection
- partial fills
- cancellation
- retries
- API failures

Prevent duplicate orders.

Every order must have an internal ID.

---

# 19. PHASE 8 — Autonomous Trading Loop

Build the complete loop:

```text
Collect Data
     ↓
Calculate Features
     ↓
Generate Signals
     ↓
Rank Opportunities
     ↓
AI Evaluation
     ↓
Risk Validation
     ↓
Execute
     ↓
Monitor Positions
     ↓
Evaluate Exit Conditions
     ↓
Log Everything
```

Make execution frequency configurable.

Do not poll unnecessarily fast.

---

# 20. Position Management

The agent must autonomously manage positions after entry.

Track:

- entry price
- current price
- unrealized P&L
- realized P&L
- Greeks
- expiration
- thesis
- invalidation condition
- risk

Possible actions:

```text
HOLD
REDUCE
EXIT
```

The risk engine still has final authority.

---

# 21. Decision Journal

Every opportunity and trade must be recorded.

Store:

```text
timestamp
underlying
market_state
features
strategy_signal
AI_decision
AI_confidence
AI_reasoning
risk_decision
execution
result
```

This is a **high-priority feature**.

The hackathon demo should be able to show:

```text
Market changed
      ↓
Agent detected opportunity
      ↓
Quant signal appeared
      ↓
AI evaluated it
      ↓
Risk engine approved it
      ↓
Trade executed
      ↓
Position monitored
      ↓
Trade outcome
```

This is much more compelling than simply showing a P&L number.

---

# 22. Kill Switch

Implement:

```text
TRADING_ENABLED=true/false
```

If false:

- no new positions
- continue monitoring existing positions

Automatic shutdown conditions:

- daily loss exceeded
- maximum drawdown exceeded
- market-data failure
- Alpaca connection failure
- unexpected system state

The agent should fail safely.

---

# 23. PHASE 9 — Minimal Dashboard

Only build this after the trading engine is working.

Use Streamlit.

Show:

## Portfolio

- portfolio value
- total P&L
- daily P&L
- drawdown
- buying power

## Positions

- contract
- quantity
- entry
- current price
- P&L
- Greeks
- expiration

## Trades

- timestamp
- strategy
- AI decision
- P&L
- result

## Agent reasoning

Show the decision chain.

## Live activity

Example:

```text
19:42:13
Detected unusual volatility

19:42:14
Momentum signal generated

19:42:15
AI confidence: 0.81

19:42:15
Risk engine: APPROVED

19:42:16
Order submitted

19:42:17
Order filled
```

If time becomes limited:

**Cut dashboard polish before cutting trading functionality.**

---

# 24. Experiment Tracking

Keep experiments simple.

Every strategy experiment should record:

```text
experiment_id
strategy
parameters
dataset
period
return
Sharpe
max_drawdown
trade_count
profit_factor
notes
```

Create a simple comparison table.

Example:

```text
Strategy       Return    Sharpe    Max DD    Trades
----------------------------------------------------
Momentum       +X%       X.XX      X%        XX
Mean Reversion +X%       X.XX      X%        XX
Volatility     +X%       X.XX      X%        XX
```

---

# 25. Paper Trading Validation

Before competition deployment, verify:

## Infrastructure

- [ ] market data works
- [ ] options data works
- [ ] orders work
- [ ] positions update
- [ ] exits work
- [ ] errors are handled
- [ ] logs work
- [ ] kill switch works

## Trading

- [ ] signals are generated
- [ ] bad trades are rejected
- [ ] position sizing works
- [ ] duplicate orders are prevented
- [ ] agent can run unattended

## AI

- [ ] structured output works
- [ ] invalid output is rejected
- [ ] AI failure doesn't crash trading
- [ ] AI cannot bypass risk

---

# 26. Strategy Selection

Do not choose the strategy because it sounds sophisticated.

Rank candidates using:

```text
Expected Edge
×
Robustness
×
Liquidity
×
Competition-window suitability
×
Implementation speed
```

The final strategy should ideally:

- operate on liquid underlyings
- have frequent enough opportunities
- have clearly defined entry/exit rules
- have controlled downside
- be explainable
- be testable
- work during the actual competition window

---

# 27. What NOT to Build

Unless there is a compelling reason, do NOT build:

- React frontend
- TypeScript frontend
- multi-provider LLM architecture
- PostgreSQL
- Kubernetes
- microservices
- vector database
- RAG
- complex agent frameworks
- multi-agent debate systems
- huge ML models
- dozens of indicators
- complicated event buses
- elaborate UI animations
- unnecessary abstractions

If a component does not improve:

**alpha, risk management, execution reliability, validation, or demo clarity**

it is probably unnecessary.

---

# 28. Critical Engineering Rules

### Rule 1

**No LLM → direct order execution.**

### Rule 2

**Risk engine is always the final authority.**

### Rule 3

**Missing data must never silently become valid data.**

### Rule 4

**Every trade must be explainable from logged inputs.**

### Rule 5

**Every strategy parameter must be configurable.**

### Rule 6

**Every experiment must be recorded.**

### Rule 7

**Never optimize against the test period.**

### Rule 8

**Never invent Alpaca API functionality.**

If unsure about an API feature, inspect the current official Alpaca documentation.

### Rule 9

**Don't build infrastructure for hypothetical future requirements.**

### Rule 10

**When behind schedule, reduce scope rather than extend architecture.**

---

# 29. Claude Code Operating Procedure

You are responsible for implementing the system, not merely describing it.

For each work session:

1. Inspect the current repository.
2. Determine what is already implemented.
3. Identify the smallest useful next step.
4. Implement it.
5. Write focused tests.
6. Run the tests.
7. Fix failures.
8. Verify the actual integration where possible.
9. Update README/documentation only when useful.
10. Report progress.

Do not spend excessive time explaining architecture before writing code.

Prefer:

```text
Build → Test → Run → Observe → Improve
```

over:

```text
Design → Abstract → Document → Refactor → Eventually Build
```

---

# 30. Checkpoint Reporting

At the end of each major work session, report:

```text
STATUS
------

Completed:
- ...

Working:
- ...

Not working:
- ...

Tests:
- ...

Paper trading:
- ...

Current strategy:
- ...

Current P&L:
- ...

Next highest-value task:
- ...

Scope cuts made:
- ...
```

---

# 31. FIRST TASK

Do **NOT** build the entire system.

Start immediately with the first critical milestone.

## Goal

**Get a real Alpaca paper-trading order executed as quickly as possible.**

Start by:

1. Inspecting the repository.
2. Initializing the Python project.
3. Setting up `.env`.
4. Connecting to Alpaca paper trading.
5. Verifying account access.
6. Retrieving live market data.
7. Retrieving an options chain.
8. Normalizing the data.
9. Creating a minimal signal.
10. Creating a minimal risk check.
11. Submitting a paper order.
12. Confirming the position exists.
13. Logging the entire cycle.

Do not build:

- dashboard
- AI
- backtester
- advanced strategy framework

until the basic:

```text
DATA
→ SIGNAL
→ RISK
→ ORDER
→ POSITION
```

pipeline works.

## First milestone

The first meaningful success condition is:

> **The agent successfully identifies a valid options contract, passes it through the deterministic risk engine, submits a paper trade to Alpaca, confirms the fill/position, and records the complete decision trail.**

Once that works, move toward strategy research and autonomous operation.
