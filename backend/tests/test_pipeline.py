from datetime import datetime, timezone

from backend.app.config.settings import Settings
from backend.app.data.mock_alpaca import MockAlpacaClient
from backend.app.data.models import (
    Greeks,
    OptionContract,
    OptionRight,
    OptionSnapshot,
    Quote,
    Signal,
)
from backend.app.pipeline import TradingLoop
from backend.app.risk.engine import RiskEngine


def _signal(**kwargs) -> Signal:
    snap = OptionSnapshot(
        contract=OptionContract(
            symbol="SPY250918C00560000",
            underlying="SPY",
            expiration=__import__("datetime").date.today() + __import__("datetime").timedelta(days=21),
            strike=560,
            right=OptionRight.CALL,
            tradable=True,
            open_interest=2500,
            volume=400,
        ),
        quote=Quote(symbol="SPY250918C00560000", bid=4.4, ask=4.6, last=4.5),
        implied_volatility=0.18,
        greeks=Greeks(delta=0.5),
        underlying_price=560,
    )
    defaults = dict(
        underlying="SPY",
        direction="long",
        confidence=0.7,
        thesis="test",
        expected_edge=0.01,
        contract=snap.contract.symbol,
        timestamp=datetime.now(timezone.utc),
        snapshot=snap,
    )
    defaults.update(kwargs)
    return Signal(**defaults)


def test_risk_rejects_wide_spread():
    settings = Settings(max_bid_ask_spread=0.02)
    engine = RiskEngine(settings)
    client = MockAlpacaClient()
    sig = _signal()
    sig.snapshot.quote.bid = 1.0
    sig.snapshot.quote.ask = 2.0
    decision = engine.evaluate(sig, client.get_account(), [])
    assert decision.approved is False
    assert any("spread" in r.lower() for r in decision.reasons)


def test_risk_rejects_kill_switch():
    settings = Settings(trading_enabled=False)
    engine = RiskEngine(settings)
    client = MockAlpacaClient()
    decision = engine.evaluate(_signal(), client.get_account(), [])
    assert decision.approved is False
    assert any("Kill switch" in r for r in decision.reasons)


def test_risk_rejects_missing_quote():
    settings = Settings()
    engine = RiskEngine(settings)
    client = MockAlpacaClient()
    sig = _signal()
    sig.snapshot.quote = None
    decision = engine.evaluate(sig, client.get_account(), [])
    assert decision.approved is False
    assert any("Missing option quote" in r for r in decision.reasons)


def test_pipeline_submits_and_confirms_position(tmp_path):
    settings = Settings(database_path=str(tmp_path / "agent.db"), underlyings="SPY")
    client = MockAlpacaClient()
    loop = TradingLoop(client, settings)
    result = loop.run_once(submit=True)
    assert result.signals
    approved = [a for a in result.actions if a["approved"]]
    assert approved
    pos = client.list_positions()
    assert pos
    assert client.submitted
