#!/usr/bin/env python3
"""
Debug script to see how many signals are generated each day.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta

# Add the backend directory to the path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.settings import Settings
from backend.app.data.mock_alpaca import MockAlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy


class HistoricalMockAlpacaClient(MockAlpacaClient):
    """
    Extended mock client that can return historical data for backtesting.
    """

    def __init__(self, initial_price: float = 450.0):
        super().__init__()
        self._spy_price = initial_price
        self._qqq_price = initial_price * 0.85  # QQQ typically lower than SPY
        self._iwm_price = initial_price * 0.5   # IWM typically lower than SPY
        self._price_history = {
            "SPY": [initial_price],
            "QQQ": [self._qqq_price],
            "IWM": [self._iwm_price]
        }
        self._day = 0
        self._volatility = 0.015  # 1.5% daily volatility

    def get_bars(self, symbol: str, *, days: int = 30) -> list:
        """
        Return historical bar data for backtesting.
        Generates realistic price movements with some trend and volatility.
        """
        from backend.app.data.models import Bar

        # Extend history by one day each time to simulate new data arriving
        # We always extend by at least one day to simulate the passage of time
        while len(self._price_history[symbol]) <= self._day:
            last_price = self._price_history[symbol][-1]

            # Add some mean reversion and trend
            if symbol == "SPY":
                trend = 0.0002  # Slight upward trend
            elif symbol == "QQQ":
                trend = 0.0003  # Slightly higher trend for tech
            else:  # IWM
                trend = 0.0001  # Slight trend for small caps

            mean_reversion = -0.05 * (self._price_history[symbol][-1] -
                                      sum(self._price_history[symbol][-10:])/min(len(self._price_history[symbol]), 10)) if len(self._price_history[symbol]) >= 10 else 0

            # Random walk with volatility
            change = trend + mean_reversion + (self._volatility * (0.5 - (hash(f"{last_price}{len(self._price_history[symbol])}") % 1000) / 500.0))
            new_price = last_price * (1 + change)
            self._price_history[symbol].append(new_price)

        # Increment the day counter for next call
        self._day += 1

        # Return the last 'days' worth of price data as bars
        start_idx = max(0, len(self._price_history[symbol]) - days)
        price_slice = self._price_history[symbol][start_idx:]
        # We don't have changes_slice in the original, but we need to generate bars
        # Let's simplify and just use the price_slice to create bars with dummy OHLC
        bars = []
        base_time = datetime.now() - timedelta(days=len(price_slice))

        for i, price in enumerate(price_slice):
            # Add some intraday volatility
            intraday_vol = abs(0.001) * 2 + 0.003  # dummy
            high = price * (1 + abs(intraday_vol * 0.5))
            low = price * (1 - abs(intraday_vol * 0.5))
            open_price = price_slice[i-1] * (1 + intraday_vol * 0.3) if i > 0 else price

            # Ensure OHLC relationships
            high = max(high, open_price, price)
            low = min(low, open_price, price)

            bar = Bar(
                symbol=symbol,
                timestamp=base_time + timedelta(days=i),
                open=open_price,
                high=high,
                low=low,
                close=price,
                volume=50_000_000 + (i * 100000)  # Increasing volume trend
            )
            bars.append(bar)

        return bars


def create_historical_market_data_service() -> MarketDataService:
    """
    Create a market data service with historical data capability.
    """
    client = HistoricalMockAlpacaClient(initial_price=450.0)
    return MarketDataService(client)


def main():
    print("=== Debugging Signal Generation ===\n")

    # Use a short date range for quick testing (10 days)
    end_date = date.today()
    start_date = end_date - timedelta(days=10)

    print(f"Backtesting from {start_date} to {end_date}")
    print(f"Period: {(end_date - start_date).days} days\n")

    # Create settings
    settings = Settings(
        underlyings="SPY,QQQ,IWM",
        max_bid_ask_spread=0.25,
        min_open_interest=0,
        min_option_volume=0,
        min_dte=0,
        max_dte=365,
        max_risk_per_trade=0.02,
        max_portfolio_exposure=0.3,
        max_positions=5,
        max_underlying_concentration=0.2,
        trading_enabled=True,
    )

    # Create market data service
    market_data = create_historical_market_data_service()

    # Create strategy
    strategy = LiquidMomentumStrategy(market_data, settings)

    # We'll simulate the backtest loop manually to see signals
    current_date = start_date
    delta = timedelta(days=1)
    total_signals = 0

    while current_date <= end_date:
        print(f"--- Date: {current_date} ---")
        # Generate market state for the strategy (simplified)
        # In reality, we would pass market_state to generate_signals, but the strategy ignores it
        # So we just call generate_signals with an empty market state
        signals = strategy.generate_signals({})
        print(f"  Signals generated: {len(signals)}")
        for signal in signals:
            print(f"    {signal.underlying} {signal.direction} {signal.contract} confidence={signal.confidence:.2f}")
        total_signals += len(signals)
        current_date += delta

    print(f"\nTotal signals over {(end_date - start_date).days} days: {total_signals}")
    print(f"Average signals per day: {total_signals / (end_date - start_date).days:.2f}")

if __name__ == "__main__":
    main()
