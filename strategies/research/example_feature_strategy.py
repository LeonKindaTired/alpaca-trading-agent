"""
Example strategy demonstrating use of the feature engine.

This is for educational purposes and not intended for live trading.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.data.models import Bar, OptionSnapshot, Signal
from backend.app.features.engine import atr, rsi, sma
from backend.app.strategies.base import Strategy


class ExampleFeatureStrategy(Strategy):
    """
    Example strategy that combines multiple features.

    This strategy demonstrates:
    1. Using SMA for trend direction
    2. Using RSI for overbought/oversold conditions
    3. Using ATR for volatility-based position sizing (conceptual)
    """

    def __init__(self, market_data_service, settings):
        # In a real strategy, you'd use the market_data_service to get data
        # For this example, we assume bars are passed in market_state
        self.market_data = market_data_service
        self.settings = settings

    def generate_signals(self, market_state: dict) -> list[Signal]:
        """
        Generate signals based on feature combinations.

        Expected market_state format:
        {
            "underlyings": ["SPY", "QQQ"],
            "bars_data": {  # Optional: pre-fetched bars
                "SPY": [Bar, Bar, ...],
                "QQQ": [Bar, Bar, ...]
            }
        }
        """
        signals = []

        # Get underlyings from market state or settings
        symbols = market_state.get("underlyings") or self.settings.underlying_list

        for symbol in symbols:
            # Get bars for this symbol (in practice, you'd get these from market_data service)
            bars = market_state.get("bars_data", {}).get(symbol, [])

            if not bars:
                # Try to get bars from market data service
                # bars = self.market_data.bars(symbol, days=30)
                continue  # Skip if no data available

            # Calculate features
            sma_20 = sma(bars, lookback=20)
            rsi_14 = rsi(bars, lookback=14)
            atr_14 = atr(bars, lookback=14)
            last_price = bars[-1].close if bars else None

            # Simple example logic (NOT a tested strategy!)
            if sma_20 is None or rsi_14 is None or last_price is None:
                continue

            # Bullish condition: price above SMA and RSI not overbought
            if last_price > sma_20 and rsi_14 < 70:
                # In a real strategy, you'd generate an options signal here
                # For this example, we'll just show how features could be used
                pass

            # Bearish condition: price below SMA and RSI not oversold
            elif last_price < sma_20 and rsi_14 > 30:
                # Again, conceptual - would generate put signal
                pass

        return signals