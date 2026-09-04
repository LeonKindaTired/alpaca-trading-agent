"""Run one paper-trading cycle.

Usage from repo root:
    python -m backend.scripts.run_paper_cycle
    python -m backend.scripts.run_paper_cycle --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.logging import setup_logging
from backend.app.config.settings import get_settings
from backend.app.data.live_alpaca import LiveAlpacaClient
from backend.app.pipeline import TradingLoop


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Do not submit orders")
    args = parser.parse_args()

    settings = get_settings()
    log = setup_logging(settings.log_level)

    if not settings.alpaca_api_key or settings.alpaca_api_key.startswith("your_"):
        log.error("Set ALPACA_API_KEY / ALPACA_SECRET_KEY in .env (paper keys).")
        return 1

    client = LiveAlpacaClient(settings)
    account = client.get_account()
    log.info("Connected. equity=%s status=%s", account.equity, account.status)
    quote = client.get_latest_quote("SPY")
    log.info("SPY quote bid=%s ask=%s", quote.bid, quote.ask)

    loop = TradingLoop(client, settings)
    result = loop.run_once(submit=not args.dry_run)

    # Print summary of what was considered and what was done
    signals_considered = len(result.signals)
    signals_approved = sum(1 for action in result.actions if action.get("approved", False))
    orders_submitted = sum(1 for action in result.actions if "order" in action and action["order"] is not None)

    print(f"\n=== TRADING CYCLE SUMMARY ===")
    print(f"Signals considered: {signals_considered}")
    print(f"Signals approved: {signals_approved}")
    print(f"Orders submitted: {orders_submitted}")
    if signals_considered > 0:
        print(f"Approval rate: {signals_approved/signals_considered*100:.1f}%")
    print("=============================\n")

    print(json.dumps({"account": result.account, "actions": result.actions}, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
