# Alpaca AI Trading Agent

Autonomous options paper-trading agent for the Alpaca AI Trading Agents Hackathon (28 Aug–4 Sep 2026).

The LLM never places orders. The deterministic risk engine is the final authority.

## Pipeline

```
Market data → features → signal → risk engine → Alpaca paper order → position → journal
```

AI supervisor, dashboard, and backtester are intentionally not built yet.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put **paper** keys in `.env` from https://app.alpaca.markets/

Hackathon submissions need a dedicated paper account with **$100,000** starting balance. Strategies must include options. Alpaca also requires using the Trading API plus MCP server or CLI — wire that in after the paper cycle works.

## Tests (no network)

```bash
pytest
```

## One paper cycle

```bash
python -m backend.scripts.run_paper_cycle --dry-run
python -m backend.scripts.run_paper_cycle
```

Health check:

```bash
uvicorn backend.app.main:app --reload
```

## Kill switch

`TRADING_ENABLED=false` blocks new positions.

## Competition window notes

See `docs/competition_window.md`. US cash session. Monday 1 Sep 2026 is Labor Day (markets closed).
