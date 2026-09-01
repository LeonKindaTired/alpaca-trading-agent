# Build a Modern Trading Dashboard

We already have an Alpaca AI options-trading agent under development.

I want you to build a **modern, polished, professional trading dashboard** for the project.

This is not an enterprise production dashboard. It is a **hackathon-quality interface** that should look impressive when a judge opens it or when we record a demo.

The dashboard should communicate:

> **"This is an autonomous AI trading system that is actually running."**

Do not make it look like a generic admin panel or default Streamlit application.

---

# 1. First: Inspect the Existing Project

Before writing code:

1. Inspect the entire repository.
2. Understand the current backend architecture.
3. Identify:

   - existing API endpoints
   - database schema
   - trading models
   - position models
   - trade history
   - AI decision logs
   - portfolio data
   - strategy outputs
   - risk engine outputs

4. Determine how the dashboard can consume the existing data.

**Do not duplicate business logic inside the dashboard.**

The dashboard is a presentation layer.

If an API endpoint is missing, create the smallest clean backend endpoint necessary.

Do not rewrite working trading logic just to accommodate the UI.

---

# 2. Dashboard Goal

The dashboard should feel like a combination of:

- modern quantitative trading terminal
- AI agent control center
- portfolio monitor
- strategy analytics interface

The visual hierarchy should immediately answer:

1. How is the agent performing?
2. What positions does it currently hold?
3. What is the agent currently thinking/doing?
4. Why did it make its recent trades?
5. What is the risk level?
6. Is the autonomous system currently active?

---

# 3. Recommended UI Direction

Use a **dark-first interface**.

Visual style:

- near-black/dark background
- subtle borders
- restrained accent color
- clean typography
- compact information density
- generous spacing
- rounded cards
- subtle shadows/glows
- professional financial-terminal aesthetic

Avoid:

- excessive gradients
- giant colorful cards
- excessive animations
- excessive rounded "SaaS startup" styling
- emoji-heavy UI
- generic Bootstrap appearance
- default Streamlit widgets wherever possible

Think:

**Bloomberg Terminal × modern AI product × Linear/Vercel-level polish**

but do not copy any specific company's interface.

---

# 4. Technology

If the current project is already using Streamlit, you may continue using Streamlit.

However, if the current dashboard implementation is too restrictive for the visual quality described below, you are allowed to use:

- Streamlit
- custom CSS
- HTML components
- Plotly

Do not introduce a completely separate frontend framework unless the existing architecture genuinely cannot achieve the required quality.

The dashboard should remain easy to run locally.

---

# 5. GLOBAL LAYOUT

Create a persistent application shell.

```text
┌──────────────────────────────────────────────────────────────┐
│ LOGO / AGENT NAME                     ● LIVE    09:42:13 UTC │
├──────────────┬───────────────────────────────────────────────┤
│              │                                               │
│  Overview    │                                               │
│              │              MAIN CONTENT                     │
│  Portfolio   │                                               │
│              │                                               │
│  Positions   │                                               │
│              │                                               │
│  Trades      │                                               │
│              │                                               │
│  Agent       │                                               │
│              │                                               │
│  Strategy    │                                               │
│              │                                               │
│  Risk        │                                               │
│              │                                               │
│  Settings    │                                               │
│              │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

Sidebar navigation:

- Overview
- Portfolio
- Positions
- Trades
- Agent
- Strategy
- Risk
- Settings

The current page should be visually obvious.

---

# 6. TOP BAR

Persistent top bar should display:

### Left

Agent identity:

```text
ALPHA
Autonomous Options Agent
```

or use the existing project/agent name if one already exists.

### Center/right

System state:

```text
● MARKET OPEN
● AGENT ONLINE
```

Use subtle status indicators.

### Right

Display:

- current time
- last data update
- paper/live environment indicator

Make it impossible to accidentally confuse the dashboard with a live-money system.

Example:

```text
PAPER TRADING
```

should be clearly visible.

---

# 7. OVERVIEW PAGE

This is the most important page.

When a judge opens the dashboard, this is what they should see.

## Hero Metrics

Create a compact metric row:

```text
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ PORTFOLIO      │ │ TODAY          │ │ TOTAL P&L      │ │ DRAWDOWN       │
│ $102,481.32    │ │ +$842.17       │ │ +$2,481.32     │ │ -1.8%          │
│ +2.48%          │ │ +0.82%         │ │                │ │                │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
```

Do not make these cards enormous.

They should be information-dense.

---

# 8. EQUITY CURVE

Create the main performance chart.

Show:

- portfolio value over time
- benchmark if available
- hover tooltips
- time range selector

Options:

```text
1D
1W
1M
ALL
```

Use Plotly or another suitable charting library.

The chart should look clean and professional.

Avoid unnecessary chart decorations.

---

# 9. LIVE AGENT ACTIVITY

This is one of the most important parts of the product.

Create a live activity panel.

Example:

```text
AGENT ACTIVITY

09:42:18
VOLATILITY SIGNAL
NVDA
IV/RV divergence detected
Confidence 82%

09:42:21
AI EVALUATION
NVDA 25 SEP 2026 180C
BUY
Confidence 84%

09:42:22
RISK CHECK
APPROVED
Risk: 0.7% portfolio

09:42:24
EXECUTION
ORDER FILLED
2 contracts @ $4.21
```

Each event should have:

- timestamp
- event type
- underlying
- concise description
- status

Use subtle visual differentiation between:

- signal
- AI decision
- risk approval
- execution
- exit
- rejection

This section should make the agent feel alive.

If WebSockets/SSE already exist, use them.

If not, implement lightweight polling.

Do not over-engineer realtime infrastructure.

---

# 10. CURRENT POSITIONS

Create a professional positions table.

Columns:

```text
Underlying
Contract
Side
Qty
Entry
Mark
P&L
P&L %
Delta
Theta
IV
Expiration
```

Allow clicking a position to see more information.

Use clear but restrained P&L indicators.

Avoid giant green/red UI.

---

# 11. POSITION DETAIL

When a position is selected, show:

### Contract

```text
NVDA
25 SEP 2026
180 CALL
```

### Performance

- entry price
- current price
- unrealized P&L
- return %

### Greeks

- delta
- gamma
- theta
- vega
- IV

### Agent thesis

Example:

```text
THESIS

Underlying momentum accelerated while implied
volatility remained below its recent realized range.

The agent expects continued directional movement
over the next 1–3 sessions.

INVALIDATION

Momentum falls below threshold
or volatility regime changes.
```

### Position timeline

```text
09:31 Signal detected
09:32 AI approved
09:32 Risk approved
09:33 Order filled
09:45 Position monitored
```

This is extremely important for the hackathon demo.

---

# 12. TRADE HISTORY

Create a dedicated trade-history page.

Table:

```text
Time
Underlying
Contract
Strategy
AI Decision
Entry
Exit
P&L
Duration
Reason
```

Allow filtering by:

- strategy
- underlying
- profitable/unprofitable
- date
- AI/quant mode

Clicking a trade should open its complete decision journal.

---

# 13. DECISION JOURNAL

This should be one of the strongest parts of the dashboard.

For each trade display the complete reasoning pipeline:

```text
MARKET STATE
      ↓
FEATURES
      ↓
QUANT SIGNAL
      ↓
AI ANALYSIS
      ↓
RISK ENGINE
      ↓
EXECUTION
      ↓
RESULT
```

Example:

```text
┌─────────────────────────────────────────────┐
│ NVDA — LONG CALL                            │
│ September 25, 2026                          │
├─────────────────────────────────────────────┤
│ SIGNAL                                      │
│ Momentum score        0.84                  │
│ Volatility regime     HIGH                   │
│ Volume anomaly        +2.3σ                  │
├─────────────────────────────────────────────┤
│ AI DECISION                                 │
│ BUY                                         │
│ Confidence            82%                   │
│                                             │
│ "Momentum and volume expansion align with   │
│ the current volatility regime..."           │
├─────────────────────────────────────────────┤
│ RISK ENGINE                                 │
│ ✓ Liquidity                                │
│ ✓ Position size                            │
│ ✓ Portfolio exposure                       │
│ ✓ Spread                                   │
│                                             │
│ APPROVED                                    │
├─────────────────────────────────────────────┤
│ EXECUTION                                   │
│ 2 contracts @ $4.21                         │
└─────────────────────────────────────────────┘
```

The exact data should come from the backend.

Do not fabricate AI reasoning.

---

# 14. STRATEGY PAGE

Show how the trading strategy is performing.

Display:

### Strategy status

```text
ACTIVE STRATEGY
Momentum + Volatility Regime
```

### Metrics

- trades
- win rate
- profit factor
- Sharpe
- Sortino
- max drawdown
- average trade

### Strategy performance

Show equity/P&L by strategy.

### Signal distribution

Show:

- BUY signals
- HOLD signals
- rejected signals
- executed signals

### Strategy configuration

Display current parameters in a read-only interface.

Do not add controls for modifying live strategy parameters unless the backend already supports safe configuration changes.

---

# 15. RISK PAGE

Make risk highly visible.

Display:

### Current risk

```text
PORTFOLIO RISK

Exposure             18.4%
Max Exposure         40%

Daily Loss           0.4%
Daily Limit          3.0%

Drawdown             1.8%
Max Drawdown         10%

Open Positions       4
Maximum              8
```

Use progress bars/gauges where useful.

Also show:

### Recent risk decisions

```text
09:42 APPROVED
NVDA CALL
Risk: 0.7%

09:18 REJECTED
TSLA PUT
Reason:
Spread > maximum threshold
```

The risk engine should visually feel like a **hard security boundary**.

---

# 16. AGENT PAGE

Create a page focused on the autonomous system.

Show:

```text
AGENT STATUS

● ONLINE

Current Mode:
AI SUPERVISOR

Last Decision:
09:42:24

Next Scan:
09:43:00
```

Then show the autonomous loop:

```text
DATA
  ✓

FEATURES
  ✓

SIGNALS
  ✓

AI
  ✓

RISK
  ✓

EXECUTION
  ✓

MONITORING
  ✓
```

If a component fails, make that obvious.

---

# 17. SYSTEM HEALTH

Show:

- Alpaca connection
- market-data status
- AI status
- database status
- execution status
- last successful heartbeat
- API latency

Example:

```text
SYSTEM HEALTH

Alpaca API          ● Healthy
Market Data         ● Healthy
AI Provider         ● Healthy
Database            ● Healthy
Execution           ● Healthy

Last heartbeat      2s ago
```

---

# 18. PAPER TRADING INDICATOR

This is mandatory.

Make it very clear throughout the application:

```text
PAPER TRADING
```

Do not use wording that could make a judge think real capital is being traded.

---

# 19. VISUAL DESIGN

Use a coherent design system.

## Typography

Use a modern sans-serif font.

Recommended:

- Inter
- Geist
- system-ui

Use monospace only for:

- prices
- timestamps
- contract symbols
- technical values

## Colors

Use a restrained palette.

Base:

- dark background
- slightly lighter cards
- subtle borders

Accent:

- one primary accent

Positive:

- green

Negative:

- red

Warning:

- amber

Do not overuse colors.

---

# 20. Cards

Cards should have:

- subtle border
- small radius
- consistent padding
- clear hierarchy

Avoid cards inside cards inside cards.

Use whitespace to separate sections.

---

# 21. Tables

Tables should feel like a professional trading interface.

Use:

- compact rows
- aligned numerical columns
- monospace numerical values
- sticky headers where useful
- hover states
- clear selected state

Avoid huge row heights.

---

# 22. Charts

Charts should be:

- clean
- dark-theme compatible
- minimal
- interactive
- responsive

Avoid:

- 3D
- excessive gridlines
- unnecessary legends
- decorative chart elements

---

# 23. Animations

Use subtle animation only where it improves understanding.

Examples:

- live status pulse
- new activity entry
- order execution notification
- page transitions if simple

Do not animate everything.

The application should feel fast.

---

# 24. RESPONSIVENESS

The primary target is:

**desktop browser**

Support reasonable resizing.

Do not spend significant time optimizing for mobile.

---

# 25. Data Architecture

The dashboard must consume real backend data.

Do NOT create fake data to make the UI look impressive unless explicitly building a development/demo fallback.

If the backend has incomplete data:

1. identify the missing endpoint/data
2. add the smallest required API
3. connect the dashboard
4. show a clear empty/loading state when data doesn't exist

Never fabricate:

- P&L
- trades
- AI decisions
- positions
- performance
- market data

---

# 26. Loading States

Every major data component needs a useful loading state.

Example:

```text
Loading portfolio...
```

Avoid blank screens.

---

# 27. Error States

Errors should be informative but not ugly.

Example:

```text
Market data unavailable

Last successful update:
09:41:52

Retrying...
```

Do not expose stack traces to normal dashboard users.

Log technical errors in the backend.

---

# 28. Empty States

If there are no positions:

```text
NO OPEN POSITIONS

The agent is currently scanning the market
for qualified opportunities.
```

If there are no trades:

```text
NO TRADES YET

Once the agent identifies and executes an
approved opportunity, it will appear here.
```

---

# 29. Demo Mode

If the real backend is not yet fully populated, create a clearly separated **development/demo data provider**.

It must be impossible to confuse demo data with real paper-trading data.

For example:

```text
DEMO DATA
```

Never silently mix mock and live data.

---

# 30. Performance

The dashboard should not hammer the Alpaca API.

The dashboard should consume backend data rather than directly polling Alpaca repeatedly.

Use reasonable refresh intervals.

For example:

```text
portfolio: 5–10 seconds
positions: 5–10 seconds
agent activity: 2–5 seconds
system health: 5 seconds
```

Make these configurable.

---

# 31. Security

Never expose:

- Alpaca API keys
- Alpaca secret keys
- AI API keys
- database credentials

Never place credentials in frontend code.

Never return secrets through API endpoints.

---

# 32. Important UX Principle

The dashboard should tell a story.

A judge should be able to open the application and understand:

```text
WHAT IS THE AGENT DOING?
        ↓
WHY IS IT DOING IT?
        ↓
WHAT DID IT TRADE?
        ↓
HOW MUCH RISK DID IT TAKE?
        ↓
DID IT WORK?
```

The UI should make this obvious without requiring someone to explain every screen.

---

# 33. Most Important Screens

If time is limited, build these in this order:

### Priority 1

Overview

### Priority 2

Live Agent Activity

### Priority 3

Positions

### Priority 4

Decision Journal

### Priority 5

Performance

### Priority 6

Risk

Everything else can be simplified or removed.

---

# 34. Do Not Overbuild

Do NOT spend hours building:

- complex navigation
- user authentication
- multi-user support
- settings management
- advanced permissions
- mobile layouts
- elaborate animations
- generic CRUD interfaces
- unnecessary frontend abstractions

This is a trading-agent hackathon.

The dashboard exists to make the **agent's intelligence, autonomy, risk management, and performance visible**.

---

# 35. Implementation Process

Work in this order:

## Step 1

Inspect existing backend/data.

## Step 2

Create the dashboard shell.

## Step 3

Build Overview.

## Step 4

Connect real portfolio/position data.

## Step 5

Build live agent activity.

## Step 6

Build decision journal.

## Step 7

Build performance charts.

## Step 8

Build risk page.

## Step 9

Polish visual design.

## Step 10

Test with:

- no trades
- one trade
- multiple positions
- rejected trade
- AI failure
- Alpaca failure
- empty database
- large P&L
- negative P&L

---

# 36. Acceptance Criteria

The dashboard is complete when:

- [ ] It looks substantially better than default Streamlit
- [ ] Dark professional trading-terminal aesthetic
- [ ] Overview page immediately communicates performance
- [ ] Portfolio data is real
- [ ] Position data is real
- [ ] Trade history is real
- [ ] AI decisions are real
- [ ] Risk decisions are real
- [ ] Live activity is visible
- [ ] Decision journal works
- [ ] Performance charts work
- [ ] Risk status is visible
- [ ] Agent status is visible
- [ ] Paper-trading status is obvious
- [ ] Loading states work
- [ ] Error states work
- [ ] No secrets are exposed
- [ ] Dashboard does not directly control trading
- [ ] Dashboard does not contain duplicated trading logic

---

# 37. Final Quality Bar

Before declaring the dashboard finished, ask:

> If a judge saw this for 30 seconds without me explaining it, would they immediately understand that this is an autonomous AI trading agent?

If the answer is no, improve the information hierarchy.

The most impressive parts should be:

1. **Live autonomous activity**
2. **Decision reasoning**
3. **Risk controls**
4. **Actual positions/trades**
5. **Performance**

The dashboard should make the underlying engineering and intelligence visible.

---

# 38. START NOW

Do not redesign the trading backend.

Do not modify working trading logic unnecessarily.

First inspect the repository and determine:

1. What dashboard currently exists
2. What backend APIs already exist
3. What data is already available
4. What data is missing
5. What the minimum backend changes are

Then implement the dashboard starting with:

```text
APP SHELL
    ↓
OVERVIEW
    ↓
LIVE AGENT ACTIVITY
    ↓
POSITIONS
    ↓
DECISION JOURNAL
```

After implementing each major section, run the application and verify the actual visual result.

Do not stop at writing code that "should work."

Actually run it.

At the end report:

```text
DASHBOARD STATUS
----------------

Implemented:
- ...

Backend endpoints added:
- ...

Pages:
- ...

Real data connected:
- ...

Mock/demo data:
- ...

Tests:
- ...

Visual improvements:
- ...

Known issues:
- ...

Next highest-value improvement:
- ...
```
