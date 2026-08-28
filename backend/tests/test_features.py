from __future__ import annotations

from datetime import datetime, timezone

from backend.app.data.models import Bar
from backend.app.features.engine import (
    atr,
    ema,
    last_close,
    momentum,
    realized_volatility,
    returns,
    rsi,
    sma,
    volume_change,
)


def _make_bar(close: float, volume: float = 1.0, high: float | None = None, low: float | None = None, open_: float | None = None) -> Bar:
    """Helper to create a test bar."""
    return Bar(
        symbol="TEST",
        timestamp=datetime.now(timezone.utc),
        open=open_ if open_ is not None else close,
        high=high if high is not None else close * 1.01,
        low=low if low is not None else close * 0.99,
        close=close,
        volume=volume,
    )


def test_returns():
    """Test returns calculation."""
    bars = [
        _make_bar(100.0),
        _make_bar(110.0),  # 10% return
        _make_bar(121.0),  # 10% return
    ]

    rets = returns(bars)
    assert rets is not None
    assert len(rets) == 2
    assert abs(rets[0] - 0.10) < 0.0001  # 10%
    assert abs(rets[1] - 0.10) < 0.0001  # 10%


def test_returns_insufficient_data():
    """Test returns with insufficient data."""
    bars = [_make_bar(100.0)]
    assert returns(bars) is None

    assert returns([]) is None


def test_returns_with_zero_close():
    """Test returns returns None when any previous close is zero."""
    bars = [
        _make_bar(100.0),
        _make_bar(0.0),   # close zero
        _make_bar(110.0),
    ]
    # Because prev.close == 0 for the second pair, the entire returns function returns None.
    rets = returns(bars)
    assert rets is None


def test_last_close():
    """Test last_close function."""
    bars = [_make_bar(100.0), _make_bar(110.0)]
    assert last_close(bars) == 110.0

    assert last_close([]) is None


def test_momentum():
    """Test momentum calculation."""
    bars = [
        _make_bar(100.0),  # day 0
        _make_bar(101.0),  # day 1
        _make_bar(102.0),  # day 2
        _make_bar(103.0),  # day 3
        _make_bar(104.0),  # day 4
        _make_bar(110.0),  # day 5 - 10% increase from day 0
    ]

    mom = momentum(bars, lookback=5)
    assert mom is not None
    assert abs(mom - 0.10) < 0.0001  # 10% increase over 5 periods


def test_momentum_insufficient_data():
    """Test momentum with insufficient data."""
    bars = [_make_bar(100.0) for _ in range(5)]  # Need lookback + 1 = 6 bars for lookback=5
    assert momentum(bars, lookback=5) is None


def test_sma():
    """Test Simple Moving Average."""
    bars = [_make_bar(float(i)) for i in range(10, 20)]  # 10, 11, 12, ..., 19

    # SMA of last 5 bars: (15+16+17+18+19)/5 = 17.0
    sma_val = sma(bars, lookback=5)
    assert sma_val is not None
    assert abs(sma_val - 17.0) < 0.0001


def test_sma_insufficient_data():
    """Test SMA with insufficient data."""
    bars = [_make_bar(100.0) for _ in range(4)]  # Need 5 bars for lookback=5
    assert sma(bars, lookback=5) is None


def test_ema():
    """Test Exponential Moving Average."""
    bars = [_make_bar(100.0) for _ in range(10)]  # All same price

    # EMA of constant series should be that constant
    ema_val = ema(bars, lookback=5)
    assert ema_val is not None
    assert abs(ema_val - 100.0) < 0.0001


def test_realized_volatility():
    """Test realized volatility calculation."""
    # Create bars with known returns: 1%, 2%, 3%, 2%, 1%
    close_prices = [100.0]
    for ret in [0.01, 0.02, 0.03, 0.02, 0.01]:
        close_prices.append(close_prices[-1] * (1 + ret))

    bars = [_make_bar(close) for close in close_prices]

    # Volatility of [0.01, 0.02, 0.03, 0.02, 0.01]
    # Mean = 0.018
    # Variance = ((0.01-0.018)^2 + (0.02-0.018)^2 + (0.03-0.018)^2 + (0.02-0.018)^2 + (0.01-0.018)^2) / 5
    #         = (0.000064 + 0.000004 + 0.000144 + 0.000004 + 0.000064) / 5
    #         = 0.00028 / 5 = 0.000056
    # Std dev = sqrt(0.000056) ≈ 0.00748

    vol = realized_volatility(bars, lookback=5)
    assert vol is not None
    assert abs(vol - 0.00748) < 0.0001


def test_realized_volatility_insufficient_data():
    """Test realized volatility with insufficient data."""
    bars = [_make_bar(100.0) for _ in range(5)]  # Need lookback + 1 = 6 for lookback=5
    assert realized_volatility(bars, lookback=5) is None


def test_rsi():
    """Test RSI calculation."""
    # Create a series that should give RSI around 50 (equal gains and losses)
    close_prices = [100.0]
    changes = [0.01, -0.01, 0.01, -0.01, 0.01, -0.01]  # Alternating +1%, -1%
    for change in changes:
        close_prices.append(close_prices[-1] * (1 + change))

    bars = [_make_bar(close) for close in close_prices]

    rsi_val = rsi(bars, lookback=6)
    assert rsi_val is not None
    # With equal magnitude gains and losses, RSI should be around 50
    assert 45 <= rsi_val <= 55


def test_rsi_all_gains():
    """Test RSI with all gains (should be 100)."""
    close_prices = [100.0]
    for _ in range(10):
        close_prices.append(close_prices[-1] * 1.01)  # 1% gains

    bars = [_make_bar(close) for close in close_prices]

    rsi_val = rsi(bars, lookback=10)
    assert rsi_val is not None
    assert rsi_val == 100.0


def test_rsi_all_losses():
    """Test RSI with all losses (should be 0)."""
    close_prices = [100.0]
    for _ in range(10):
        close_prices.append(close_prices[-1] * 0.99)  # 1% losses

    bars = [_make_bar(close) for close in close_prices]

    rsi_val = rsi(bars, lookback=10)
    assert rsi_val is not None
    assert rsi_val == 0.0


def test_atr():
    """Test Average True Range."""
    # Create bars with known true ranges
    bars = [
        _make_bar(100.0, high=105.0, low=95.0, open_=100.0),  # TR = max(10, 5, 5) = 10
        _make_bar(105.0, high=110.0, low=100.0, open_=105.0), # TR = max(10, 5, 10) = 10
        _make_bar(110.0, high=115.0, low=105.0, open_=110.0), # TR = max(10, 5, 5) = 10
        _make_bar(115.0, high=120.0, low=110.0, open_=115.0), # TR = max(10, 5, 10) = 10
    ]

    atr_val = atr(bars, lookback=3)
    assert atr_val is not None
    assert abs(atr_val - 10.0) < 0.0001


def test_atr_insufficient_data():
    """Test ATR with insufficient data."""
    bars = [_make_bar(100.0) for _ in range(2)]  # Need lookback + 1 = 4 for lookback=3
    assert atr(bars, lookback=3) is None


def test_volume_change():
    """Test volume change calculation."""
    bars = [
        _make_bar(100.0, volume=100.0),
        _make_bar(101.0, volume=110.0),  # 10% increase
        _make_bar(102.0, volume=90.0),   # -18.2% vs previous
    ]

    # Volume change of last bar vs average of previous 2
    # Average volume of first 2 = (100 + 110)/2 = 105
    # Volume change = (90 - 105) / 105 = -15/105 = -0.1428
    vol_change = volume_change(bars, lookback=2)
    assert vol_change is not None
    assert abs(vol_change - (-0.1428)) < 0.001


def test_volume_change_insufficient_data():
    """Test volume change with insufficient data."""
    bars = [_make_bar(100.0, volume=100.0) for _ in range(2)]  # Need lookback + 1 = 3 for lookback=2
    assert volume_change(bars, lookback=2) is None