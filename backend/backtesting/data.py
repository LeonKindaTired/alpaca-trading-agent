"""
Historical data management for backtesting.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from backend.app.data.models import Bar


@dataclass
class HistoricalBar:
    """Historical bar data compatible with backend.app.data.models.Bar."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None

    def to_backend_bar(self) -> Bar:
        """Convert to backend Bar model."""
        return Bar(
            symbol=self.symbol,
            timestamp=self.timestamp,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
        )


class HistoricalDataManager:
    """
    Manages historical market data for backtesting.

    In a production system, this would connect to a historical data provider
    or load data from a local database/file system.
    For this implementation, we'll simulate data retrieval.
    """

    def __init__(self):
        # In a real implementation, this might load data from disk or a database
        self._data_cache: Dict[str, pd.DataFrame] = {}

    def get_historical_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: str = "1Day"
    ) -> List[HistoricalBar]:
        """
        Get historical bar data for a symbol.

        Args:
            symbol: The symbol to get data for (e.g., "SPY")
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            timeframe: Timeframe of bars (e.g., "1Day", "1Hour")

        Returns:
            List of HistoricalBar objects sorted by timestamp
        """
        # For this implementation, we'll generate synthetic data
        # In a real system, you would fetch from Alpaca historical data API
        # or load from a local data store

        cache_key = f"{symbol}_{start_date}_{end_date}_{timeframe}"
        if cache_key in self._data_cache:
            df = self._data_cache[cache_key]
        else:
            # Generate synthetic price data for demonstration
            df = self._generate_synthetic_price_data(symbol, start_date, end_date, timeframe)
            self._data_cache[cache_key] = df

        # Convert DataFrame to list of HistoricalBar objects
        bars = []
        for _, row in df.iterrows():
            bar = HistoricalBar(
                symbol=symbol,
                timestamp=row['timestamp'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume')
            )
            bars.append(bar)

        return bars

    def _generate_synthetic_price_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Generate synthetic price data for backtesting purposes.
        This is only for demonstration - in practice, use real historical data.
        """
        # Determine number of periods based on timeframe
        if timeframe == "1Day":
            delta = timedelta(days=1)
        elif timeframe == "1Hour":
            delta = timedelta(hours=1)
        else:
            # Default to daily
            delta = timedelta(days=1)

        # Generate date range
        current = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.min.time())
        dates = []
        while current <= end_datetime:
            dates.append(current)
            current += delta

        # Generate synthetic price data with some randomness
        np.random.seed(hash(symbol) % 2**32)  # Deterministic seed based on symbol

        n_periods = len(dates)
        # Start with a base price
        base_price = 100.0 if symbol == "SPY" else 50.0

        # Generate returns with some drift and volatility
        daily_return_mean = 0.0005  # ~0.05% daily return
        daily_return_std = 0.01     # ~1% daily volatility

        returns = np.random.normal(daily_return_mean, daily_return_std, n_periods)
        # Add some autocorrelation to make it more realistic
        for i in range(1, n_periods):
            returns[i] += 0.1 * returns[i-1]

        # Calculate prices
        prices = base_price * np.exp(np.cumsum(returns))

        # Generate OHLC data
        opens = prices * (1 + np.random.normal(0, 0.005, n_periods))
        closes = prices * (1 + np.random.normal(0, 0.005, n_periods))
        highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.01, n_periods)))
        lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.01, n_periods)))

        # Generate volume data
        base_volume = 1000000 if symbol == "SPY" else 500000
        volumes = base_volume * (1 + np.random.normal(0, 0.3, n_periods))
        volumes = np.maximum(volumes, 1000)  # Ensure minimum volume

        # Create DataFrame
        df = pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

        return df

    def get_latest_bar(self, symbol: str) -> Optional[HistoricalBar]:
        """
        Get the most recent bar for a symbol.
        For backtesting, this would typically be the last bar in the dataset.
        """
        # This is a simplified implementation
        # In practice, you'd maintain a pointer to the current bar in your backtest
        return None