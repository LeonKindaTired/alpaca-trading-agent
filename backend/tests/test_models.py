from datetime import date, timedelta

from backend.app.data.models import OptionSnapshot, OptionContract, OptionRight, Quote
from backend.app.features.engine import momentum
from backend.app.data.models import Bar
from datetime import datetime, timezone


def test_missing_quote_fields_stay_none():
    q = Quote(symbol="SPY", bid=None, ask=None)
    assert q.mid is None
    assert q.spread_pct is None


def test_dte_computed():
    snap = OptionSnapshot(
        contract=OptionContract(
            symbol="X",
            underlying="SPY",
            expiration=date.today() + timedelta(days=10),
            strike=100,
            right=OptionRight.CALL,
        ),
        quote=None,
    )
    assert snap.dte == 10


def test_momentum_none_without_bars():
    assert momentum([]) is None
    bars = [
        Bar(
            symbol="SPY",
            timestamp=datetime.now(timezone.utc),
            open=1,
            high=1,
            low=1,
            close=100,
            volume=1,
        ),
        Bar(
            symbol="SPY",
            timestamp=datetime.now(timezone.utc),
            open=1,
            high=1,
            low=1,
            close=110,
            volume=1,
        ),
    ]
    # lookback 5 needs more bars
    assert momentum(bars, lookback=5) is None
