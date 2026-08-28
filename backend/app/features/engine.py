from __future__ import annotations

from backend.app.data.models import Bar


def returns(bars: list[Bar]) -> list[float] | None:
    if len(bars) < 2:
        return None
    out: list[float] = []
    for prev, cur in zip(bars, bars[1:]):
        if prev.close is None or cur.close is None or prev.close == 0:
            return None
        out.append(cur.close / prev.close - 1.0)
    return out


def realized_volatility(bars: list[Bar], lookback: int = 20) -> float | None:
    """Calculate realized volatility as standard deviation of returns."""
    if len(bars) < lookback + 1:
        return None
    rets = returns(bars[-(lookback + 1):])
    if rets is None or len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / len(rets)
    return variance ** 0.5


def sma(bars: list[Bar], lookback: int = 20) -> float | None:
    """Simple Moving Average."""
    if len(bars) < lookback:
        return None
    closes = [bar.close for bar in bars[-lookback:] if bar.close is not None]
    if len(closes) < lookback:
        return None
    return sum(closes) / lookback


def ema(bars: list[Bar], lookback: int = 20) -> float | None:
    """Exponential Moving Average."""
    if len(bars) < lookback:
        return None
    closes = [bar.close for bar in bars if bar.close is not None]
    if len(closes) < lookback:
        return None

    multiplier = 2 / (lookback + 1)
    ema = closes[0]  # Start with first close
    for close in closes[1:]:
        ema = (close * multiplier) + (ema * (1 - multiplier))
    return ema


def momentum(bars: list[Bar], lookback: int = 5) -> float | None:
    if len(bars) < lookback + 1:
        return None
    start = bars[-lookback - 1].close
    end = bars[-1].close
    if start is None or end is None or start == 0:
        return None
    return end / start - 1.0


def volume_change(bars: list[Bar], lookback: int = 20) -> float | None:
    """Volume change percentage vs average volume."""
    if len(bars) < lookback + 1:
        return None
    volumes = [bar.volume for bar in bars if bar.volume is not None]
    if len(volumes) < lookback + 1:
        return None
    recent_volume = volumes[-1]
    avg_volume = sum(volumes[-(lookback+1):-1]) / lookback
    if avg_volume == 0:
        return None
    return (recent_volume - avg_volume) / avg_volume


def atr(bars: list[Bar], lookback: int = 14) -> float | None:
    """Average True Range."""
    if len(bars) < lookback + 1:
        return None
    recent_bars = bars[-(lookback + 1):]
    true_ranges = []
    for i in range(1, len(recent_bars)):
        high = recent_bars[i].high
        low = recent_bars[i].low
        prev_close = recent_bars[i-1].close
        if high is None or low is None or prev_close is None:
            return None
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_ranges.append(max(tr1, tr2, tr3))
    if len(true_ranges) < lookback:
        return None
    return sum(true_ranges[-lookback:]) / lookback


def rsi(bars: list[Bar], lookback: int = 14) -> float | None:
    """Relative Strength Index."""
    if len(bars) < lookback + 1:
        return None
    rets = returns(bars[-(lookback + 1):])
    if rets is None or len(rets) < lookback:
        return None

    gains = [r if r > 0 else 0 for r in rets]
    losses = [-r if r < 0 else 0 for r in rets]

    avg_gain = sum(gains) / lookback
    avg_loss = sum(losses) / lookback

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def last_close(bars: list[Bar]) -> float | None:
    if not bars:
        return None
    return bars[-1].close
