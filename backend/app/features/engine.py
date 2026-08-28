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


def momentum(bars: list[Bar], lookback: int = 5) -> float | None:
    if len(bars) < lookback + 1:
        return None
    start = bars[-lookback - 1].close
    end = bars[-1].close
    if start is None or end is None or start == 0:
        return None
    return end / start - 1.0


def last_close(bars: list[Bar]) -> float | None:
    if not bars:
        return None
    return bars[-1].close
