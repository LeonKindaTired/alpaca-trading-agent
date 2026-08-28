# Feature Engine

This module provides technical analysis features for the trading agent.

## Available Features

### Price-Based Features
- `returns(bars, lookback=None)`: Calculate periodic returns
- `momentum(bars, lookback=5)`: Price momentum over lookback period
- `sma(bars, lookback=20)`: Simple Moving Average
- `ema(bars, lookback=20)`: Exponential Moving Average

### Volatility Features
- `realized_volatility(bars, lookback=20)`: Historical volatility as std dev of returns
- `atr(bars, lookback=14)`: Average True Range

### Volume Features
- `volume_change(bars, lookback=20)`: Volume change vs average volume

### Momentum Oscillators
- `rsi(bars, lookback=14)`: Relative Strength Index

### Utility
- `last_close(bars)`: Most recent closing price

## Usage

```python
from backend.app.features.engine import rsi, sma, realized_volatility
from backend.app.data.models import Bar

# Assume we have a list of Bar objects
bars: list[Bar] = get_market_data()

# Calculate features
rsi_value = rsi(bars, lookback=14)
sma_value = sma(bars, lookback=20)
volatility = realized_volatility(bars, lookback=20)

# Features return None if insufficient data or invalid inputs
if rsi_value is not None and rsi_value < 30:
    # Oversold condition
    pass
```

## Data Handling

All feature functions return `None` when:
- Insufficient data is provided
- Input data contains invalid values (None prices, etc.)
- Mathematical operations would be undefined (division by zero)

This follows the core principle: **missing data must never silently become valid data**.

## Testing

See `backend/tests/test_features.py` for comprehensive tests of all feature functions.