"""
Simple test to examine momentum values in our generated data.
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import hashlib

# Add the backend directory to the path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.settings import Settings
from backend.app.data.mock_alpaca import MockAlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.app.features.engine import momentum, last_close


class SimpleMockAlpacaClient(MockAlpacaClient):
    """
    Simpler mock client with more predictable price generation.
    """

    def __init__(self, initial_price: float = 450.0):
        super().__init__()
        self._spy_price = initial_price
        self._qqq_price = initial_price * 0.85
        self._iwm_price = initial_price * 0.5
        self._price_history = {
            "SPY": [initial_price],
            "QQQ": [self._qqq_price],
            "IWM": [self._iwm_price]
        }
        self._day = 0
        # Use a simpler, more predictable pattern
        self._base_volatility = 0.01

    def get_bars(self, symbol: str, *, days: int = 30) -> list:
        """
        Return historical bar data with more predictable generation.
        """
        from backend.app.data.models import Bar

        # Use a simple cyclic pattern plus small random walk
        import math
        import random

        # Set seed for reproducibility
        random.seed(42 if symbol == "SPY" else 43 if symbol == "QQQ" else 44)

        # Extend history if needed
        while len(self._price_history[symbol]) < days:
            last_price = self._price_history[symbol][-1]

            # Different trends for different symbols
            if symbol == "SPY":
                trend = 0.0001  # Very slight upward trend
            elif symbol == "QQQ":
                trend = 0.0002  # Slight upward trend
            else:  # IWM
                trend = -0.00005  # Very slight downward trend

            # Cyclical component (simulating market cycles)
            day_in_cycle = len(self._price_history[symbol]) % 20
            cyclical = 0.005 * math.sin(2 * math.pi * day_in_cycle / 20)  # 20-day cycle

            # Random walk with volatility
            random_component = random.gauss(0, self._base_volatility)

            change = trend + cyclical * 0.1 + random_component  # Scale down cyclical
            new_price = max(1.0, last_price * (1 + change))  # Prevent negative prices
            self._price_history[symbol].append(new_price)

        # Return the last 'days' worth of price data as bars
        start_idx = max(0, len(self._price_history[symbol]) - days)
        price_slice = self._price_history[symbol][start_idx:]

        bars = []
        base_time = datetime.now() - timedelta(days=len(price_slice))

        for i, price in enumerate(price_slice):
            # Add some intraday volatility
            if i > 0:
                prev_price = price_slice[i-1]
                intraday_vol = abs(price - prev_price) / prev_price * 0.5 + 0.005
            else:
                intraday_vol = 0.01

            high = price * (1 + intraday_vol)
            low = price * (1 - intraday_vol)
            open_price = price_slice[i-1] * (1 + intraday_vol * 0.5) if i > 0 else price

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
                volume=50_000_000
            )
            bars.append(bar)

        return bars


def test_momentum_values():
    """Test what momentum values we're getting."""
    print("=== Testing Momentum Values ===\n")

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

    client = SimpleMockAlpacaClient(initial_price=450.0)
    market_data = MarketDataService(client)

    lookback_periods = [3, 5, 7, 10, 15, 20]
    analysis_periods = [10, 15, 20, 25, 30]

    print(f"{'Symbol':<5} {'Lookback':<8} {'Analysis':<8} {'Momentum':<10} {'Signal?':<8} {'Close':<8}")
    print("-" * 55)

    for symbol in ["SPY", "QQQ", "IWM"]:
        for lookback in lookback_periods:
            for analysis in analysis_periods:
                if lookback >= analysis:
                    continue  # Need lookback < analysis

                bars = market_data.bars(symbol, days=analysis)
                if len(bars) >= lookback:
                    mom = momentum(bars, lookback=lookback)
                    close = last_close(bars)

                    signal_possible = mom is not None and close is not None and abs(mom) >= 0.004

                    print(f"{symbol:<5} {lookback:<8} {analysis:<8} {mom:>9.4f} ({mom:>6.2%}) "
                          f"{'YES' if signal_possible else 'NO':<8} {close:>7.2f}")
                else:
                    print(f"{symbol:<5} {lookback:<8} {analysis:<8} {'N/A':<10} {'N/A':<8} {'N/A':<8}")
            print()  # Blank line between symbols
        print("=" * 55)  # Double line between symbol groups


def test_signal_generation():
    """Test actual signal generation with different thresholds."""
    print("\n\n=== Testing Signal Generation with Different Thresholds ===\n")

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

    client = SimpleMockAlpacaClient(initial_price=450.0)
    market_data = MarketDataService(client)

    thresholds = [0.001, 0.002, 0.003, 0.004, 0.005, 0.008, 0.010, 0.015, 0.020]

    print(f"{'Threshold':<10} {'SPY':<8} {'QQQ':<8} {'IWM':<8} {'Total':<8}")
    print("-" * 40)

    for threshold in thresholds:
        # Temporarily modify strategy threshold
        from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy

        # Create a custom strategy class with the specific threshold
        class ThresholdLiquidMomentumStrategy(LiquidMomentumStrategy):
            def __init__(self, market, settings, threshold):
                super().__init__(market, settings)
                self.threshold = threshold

        strategy = ThresholdLiquidMomentumStrategy(market_data, settings, threshold)

        # Create market state
        bars_spy = market_data.bars("SPY", days=20)
        bars_qqq = market_data.bars("QQQ", days=20)
        bars_iwm = market_data.bars("IWM", days=20)

        market_state = {
            "underlyings": ["SPY", "QQQ", "IWM"],
            "bars_data": {
                "SPY": bars_spy,
                "QQQ": bars_qqq,
                "IWM": bars_iwm
            }
        }

        # Generate signals
        signals = strategy.generate_signals(market_state)

        # Count signals by underlying
        spy_signals = sum(1 for s in signals if s.underlying == "SPY")
        qqq_signals = sum(1 for s in signals if s.underlying == "QQQ")
        iwm_signals = sum(1 for s in signals if s.underlying == "IWM")
        total_signals = len(signals)

        print(f"{threshold:<10.3f} {spy_signals:<8} {qqq_signals:<8} {iwm_signals:<8} {total_signals:<8}")


if __name__ == "__main__":
    test_momentum_values()
    test_signal_generation()