# HACKATHON MODE — Upgrade Trading AI Agent

I have **only 2 days until the hackathon deadline**, so prioritize a working, polished implementation over building an overly complex trading system.

**DO NOT rewrite the application.**
**DO NOT introduce unnecessary infrastructure.**
**DO NOT spend time building a sophisticated backtesting framework unless the existing project already has one.**

First inspect the existing codebase and understand the current strategy, Alpaca integration, options selection, risk engine, trading loop, configuration, and dashboard.

Then implement the following upgrades with the smallest clean changes possible.

---

# PRIMARY GOAL

Upgrade the current simple:

```text
3-day momentum → CALL/PUT → risk checks → order
```

into:

```text
Market Regime
      ↓
Multi-factor Signal
      ↓
Signal Score
      ↓
Best Option Contract
      ↓
Risk Checks
      ↓
Trade
```

The goal is NOT maximum theoretical sophistication.

The goal is a **reliable, explainable AI trading agent that looks substantially more intelligent than a simple momentum bot during the hackathon demo.**

---

# 1. KEEP CURRENT RISK SETTINGS

Keep these defaults:

```env
MAX_RISK_PER_TRADE=0.005

MAX_PORTFOLIO_EXPOSURE=0.15

MAX_DAILY_LOSS=0.015

MAX_DRAWDOWN=0.08

MAX_POSITIONS=4

MAX_SAME_DIRECTION=2

MAX_CORRELATED_POSITIONS=2

MAX_UNDERLYING_CONCENTRATION=0.10

MAX_SECTOR_CONCENTRATION=0.10

MAX_BID_ASK_SPREAD=0.02

MIN_OPTION_VOLUME=100

MIN_OPEN_INTEREST=500

MIN_DTE=14

MAX_DTE=45

TARGET_DELTA_MIN=0.35

TARGET_DELTA_MAX=0.65

MIN_SIGNAL_SCORE=70

LOOP_INTERVAL_SECONDS=60

UNDERLYINGS=SPY,QQQ,IWM,DIA,EFA,EEM,GLD,SLV,TLT,IEF,HYG,LQD,USO,XLF,XLK,XLE,XLI,XLV,XLY,XLP,XLU,XLB,XLC,SMH,SOXX,IGV,XBI,XOP,OIH,KRE,KBE,XRT,IYR,VNQ,ITB,XHB,GDX,GDXJ,TAN,ARKK,EWJ,EWG,EWZ,FXI,INDA,ACWI,VT,DBC,UNG,DBA
```

Do not hardcode these values.

---

# 2. MULTI-FACTOR SIGNAL

Replace the single 3-day momentum trigger with a simple multi-factor scoring system.

Use:

### Trend

- Price vs 20DMA
- Price vs 50DMA
- Price vs 200DMA

### Momentum

- 5-day return
- 20-day return
- RSI(14)

### Relative Strength

Compare the underlying's recent performance against SPY.

### Volatility

Use ATR or realized volatility if already available.

Keep this implementation simple.

Do NOT build an overly complicated quantitative model.

---

# 3. SIGNAL SCORE

Every candidate should receive a score from 0–100.

Use approximately:

```text
Trend               25 points
Momentum            20 points
Relative Strength   15 points
RSI / Reversion     10 points
Volatility           10 points
Market Regime        20 points
```

Only candidates with:

```env
MIN_SIGNAL_SCORE=70
```

should proceed to option selection.

The score should explain WHY the trade was generated.

Example:

```text
QQQ CALL
Signal Score: 84

Trend: 23/25
Momentum: 18/20
Relative Strength: 14/15
Mean Reversion: 7/10
Volatility: 8/10
Regime: 14/20
```

---

# 4. MARKET REGIME

Implement a lightweight regime detector.

Use SPY as the primary reference.

Classify:

```text
BULL_TREND
BEAR_TREND
RANGE_BOUND
HIGH_VOLATILITY
```

Use simple indicators already available in the system.

For example:

```text
Price > 200DMA + positive momentum
→ BULL_TREND

Price < 200DMA + negative momentum
→ BEAR_TREND

No strong trend
→ RANGE_BOUND

Very elevated volatility
→ HIGH_VOLATILITY
```

Do not over-engineer this.

The regime should influence signal scoring.

---

# 5. STRATEGY TYPES

Implement three lightweight signal types:

## Trend Momentum

Strong trend + momentum alignment.

## Mean Reversion

Detect significant short-term overextension using RSI/Bollinger Bands/price deviation where available.

## Relative Strength

Rank the scanned universe and identify assets substantially stronger or weaker than SPY.

These do NOT need to be three completely separate systems.

They can be simple modules feeding the same signal scorer.

---

# 6. DO NOT TRADE CORRELATED SIGNALS BLINDLY

This is important.

The current system can generate:

```text
SPY PUT
QQQ PUT
IWM PUT
```

Those are three separate tickers but largely the same macro thesis.

Add simple correlation/concentration protection.

At minimum:

```env
MAX_SAME_DIRECTION=2
MAX_CORRELATED_POSITIONS=2
MAX_SECTOR_CONCENTRATION=0.10
```

If multiple highly correlated candidates appear:

**select the highest-scoring one instead of taking all of them.**

Do not build a sophisticated factor model.

A simple historical-return correlation calculation is sufficient.

---

# 7. BETTER OPTION SELECTION

Once the system decides:

```text
QQQ → bullish
```

do NOT simply choose the first available call.

Search the option chain and rank contracts using:

```text
DTE
Delta
Bid/ask spread
Volume
Open interest
Premium
IV if available
```

Preferred defaults:

```env
MIN_DTE=14
MAX_DTE=45

TARGET_DELTA_MIN=0.35
TARGET_DELTA_MAX=0.65

MAX_BID_ASK_SPREAD=0.02

MIN_OPTION_VOLUME=100
MIN_OPEN_INTEREST=500
```

Select the best valid contract.

If the first contract fails liquidity, continue searching the chain.

---

# 8. CONTRACT SCORE

Give each valid option contract a simple score.

Prefer:

- Delta close to 0.50
- Higher volume
- Higher open interest
- Lower spread
- Reasonable DTE
- Reasonable premium

Example:

```text
Contract Score: 91

Delta: 0.52
DTE: 27
Spread: 1.1%
Volume: 2,340
Open Interest: 8,120
```

This will make the agent's decision-making much easier to demonstrate.

---

# 9. CANDIDATE RANKING

Do not immediately trade the first underlying that produces a signal.

Instead:

```text
Scan universe
      ↓
Generate candidates
      ↓
Score candidates
      ↓
Filter invalid candidates
      ↓
Rank candidates
      ↓
Select strongest opportunities
      ↓
Risk checks
      ↓
Execute
```

Example:

```text
1. SMH CALL — 88
2. QQQ CALL — 84
3. SPY CALL — 78
4. XLF CALL — 73
5. IWM CALL — 69
```

If candidates are highly correlated, select the strongest one.

---

# 10. PRESERVE THE DETERMINISTIC RISK ENGINE

This is non-negotiable.

The strategy can generate ideas.

The risk engine has final authority.

Never allow the AI/strategy layer to override:

```text
MAX_RISK_PER_TRADE
MAX_PORTFOLIO_EXPOSURE
MAX_DAILY_LOSS
MAX_DRAWDOWN
MAX_POSITIONS
MAX_UNDERLYING_CONCENTRATION
MAX_SECTOR_CONCENTRATION
MAX_SAME_DIRECTION
MAX_CORRELATED_POSITIONS
MAX_BID_ASK_SPREAD
MIN_OPTION_VOLUME
MIN_OPEN_INTEREST
MIN_DTE
MAX_DTE
```

---

# 11. PREVENT DUPLICATE ORDERS

Because the loop runs every 60 seconds, make sure the agent doesn't repeatedly submit the same trade.

Before submitting:

```text
Is this contract already held?
Is there already a pending order?
Was the same signal recently submitted?
```

If yes, skip it.

Keep this simple.

---

# 12. EXPLAINABILITY

This is particularly important for the hackathon.

Every candidate should expose:

```text
Underlying
Direction
Strategy
Signal Score
Market Regime
Confidence
Reasons
Selected Option
DTE
Delta
Spread
Volume
Open Interest
Risk Amount
Approval/Rejection
```

Example:

```text
QQQ — LONG CALL

Signal Score: 84
Regime: BULL TREND

Why:
✓ Price above 50DMA
✓ Price above 200DMA
✓ 20D momentum positive
✓ Strong relative strength vs SPY
✓ RSI confirms momentum
✓ Option liquidity acceptable

Contract:
QQQ Sep 2026 Call
DTE: 27
Delta: 0.52
Spread: 1.1%
OI: 8,120

Risk:
$480
Portfolio Exposure: 4.2%

Decision:
APPROVED
```

This should be visible in the dashboard/logs.

---

# 13. DASHBOARD — ONLY HIGH-VALUE CHANGES

Do not redesign the entire dashboard if it already works.

Add the information that makes the agent impressive in a demo:

### Market Regime

```text
BULL TREND
Confidence: 82%
```

### Agent Status

```text
RUNNING
Last Scan: 17:14:02
Candidates: 42
Qualified: 7
Trades: 2
```

### Opportunity Table

```text
Symbol | Direction | Strategy | Score | Contract | Delta | DTE
```

### Portfolio Risk

```text
Exposure
Daily P/L
Drawdown
Open Positions
Risk Used
```

### Decision Log

Show:

```text
17:14
QQQ CALL
Score: 84
APPROVED

17:14
XBI CALL
Score: 76
REJECTED
Spread too wide: 21.8%

17:14
IWM PUT
Score: 72
REJECTED
Correlation limit
```

The dashboard should make it obvious that the agent is **thinking, filtering, ranking, and managing risk**.

---

# 14. DO NOT BUILD THESE THINGS RIGHT NOW

Because the hackathon deadline is in 2 days, explicitly avoid:

- Complex machine-learning models
- Reinforcement learning
- Sophisticated options spreads
- Full portfolio optimization
- Large external data pipelines
- Complex backtesting infrastructure
- New databases unless absolutely necessary
- Major frontend rewrites
- New cloud infrastructure
- Unnecessary dependencies

If something isn't required for the demo or core functionality, defer it.

---

# 15. IMPLEMENTATION PRIORITY

Work in this order:

### P0 — Must work

1. Inspect existing architecture.
2. Preserve Alpaca integration.
3. Preserve risk engine.
4. Implement multi-factor signal.
5. Implement signal scoring.
6. Implement better option selection.
7. Prevent duplicate orders.

### P1 — Demo-critical

8. Market regime.
9. Candidate ranking.
10. Explainable decision output.
11. Dashboard opportunity table.
12. Dashboard risk/decision log.

### P2 — Only if time remains

13. Strategy attribution.
14. Additional metrics.
15. UI polish.
16. Additional strategy improvements.

Do not start P2 until P0 and P1 are working.

---

# 16. DEVELOPMENT PROCESS

Before changing code:

1. Inspect the repository.
2. Identify the existing architecture.
3. Identify where the current momentum strategy lives.
4. Identify the options selector.
5. Identify the risk engine.
6. Identify the trading loop.
7. Identify dashboard components.

Then implement the smallest clean architecture that supports the above.

After each major change:

- Run the existing tests.
- Run lint/type checks if available.
- Run the agent in paper trading/simulation mode if available.
- Verify that no real order can accidentally be submitted during development.

Do not break existing functionality just to improve architecture.

---

# 17. FINAL DELIVERABLE

At the end, give me:

```text
1. Files changed
2. Features implemented
3. Configuration changes
4. Tests run
5. Any bugs/issues discovered
6. Exact command to run the agent
7. Exact command to run the dashboard
8. Recommended 5-minute hackathon demo flow
```

Most importantly:

**Optimize for a polished working hackathon submission, not theoretical trading sophistication.**

If you encounter a choice between:

A. sophisticated implementation that may take hours and introduce bugs

and

B. simpler implementation that works reliably and is easy to demonstrate

choose **B**.
