"""
Test script to run a paper trading cycle with each strategy.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the backend directory to the path so we can import from backend.app
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.logging import setup_logging
from backend.app.config.settings import get_settings
from backend.app.data.live_alpaca import LiveAlpacaClient
from backend.app.pipeline import TradingLoop
from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy
from strategies.research.volatility_mispricing import VolatilityMispricingStrategy
from strategies.research.mean_reversion import MeanReversionStrategy


def test_strategy(strategy_name: str, strategy_instance) -> None:
    """Run one dry-run cycle with the given strategy."""
    print(f"\n=== Testing {strategy_name} ===")
    settings = get_settings()
    log = setup_logging(settings.log_level)

    # Override the strategy in the settings? No, we pass it directly to TradingLoop
    client = LiveAlpacaClient(settings)
    # We want to use our custom strategy, so we create a TradingLoop with it
    # Note: TradingLoop expects a market data service and settings in its __init__
    # But we have the TradingLoop class that creates the strategy internally.
    # Instead, we can use the build_live_loop function and then replace the strategy?
    # Or we can create a custom TradingLoop-like class.

    # Let's just use the existing TradingLoop but we need to inject our strategy.
    # We'll modify the TradingLoop to accept a strategy factory or instance.

    # Since we don't want to modify the pipeline, let's create a simple loop that mimics TradingLoop.
    from backend.app.data.market_data import MarketDataService
    from backend.app.database.db import Database
    from backend.app.execution.engine import ExecutionEngine
    from backend.app.risk.engine import RiskEngine

    market = MarketDataService(client)
    db = Database(settings.database_path)
    risk = RiskEngine(settings)
    execution = ExecutionEngine(client, db)
    log = setup_logging(settings.log_level)

    # We'll create a simple loop that does one iteration
    account = client.get_account()
    positions = client.list_positions()
    log.info(
        "Account equity=%.2f buying_power=%.2f positions=%d trading_enabled=%s",
        account.equity,
        account.buying_power,
        len(positions),
        settings.trading_enabled,
    )

    # Generate signals using our strategy
    signals = strategy_instance.generate_signals({"underlyings": settings.underlying_list})
    log.info("Generated %d signal(s)", len(signals))

    # We won't actually execute orders in this test, just see if we can generate signals
    for signal in signals:
        log.info("Signal: %s", signal.thesis)

    # Return the number of signals for verification
    return len(signals)


def main() -> int:
    settings = get_settings()
    client = LiveAlpacaClient(settings)
    from backend.app.data.market_data import MarketDataService
    market = MarketDataService(client)

    strategies = [
        ("liquid_momentum", LiquidMomentumStrategy(market, settings)),
        ("volatility_mispricing", VolatilityMispricingStrategy(market, settings)),
        ("mean_reversion", MeanReversionStrategy(market, settings)),
    ]

    total_signals = 0
    for name, strategy in strategies:
        try:
            count = test_strategy(name, strategy)
            total_signals += count
            print(f"{name}: {count} signals")
        except Exception as e:
            print(f"Error testing {name}: {e}")
            import traceback
            traceback.print_exc()
            return 1

    print(f"\nTotal signals across all strategies: {total_signals}")
    return 0 if total_signals >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())