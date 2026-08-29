from __future__ import annotations

from datetime import datetime, timezone

from backend.app.config.settings import Settings
from backend.app.data.market_data import MarketDataService
from backend.app.data.models import OptionSnapshot, Signal
from backend.app.features.engine import last_close, momentum
from backend.app.strategies.base import Strategy


class LiquidMomentumStrategy(Strategy):
    """Minimal directional options signal on liquid ETFs.

    Buys a near-ATM call after short-horizon upside momentum, or a put after
    downside momentum. Contract selection prefers tight spreads and open interest.
    """

    name = "liquid_momentum"
    threshold = 0.003

    def __init__(self, market: MarketDataService, settings: Settings) -> None:
        self.market = market
        self.settings = settings

    def generate_signals(self, market_state: dict) -> list[Signal]:
        symbols = market_state.get("underlyings") or self.settings.underlying_list
        signals: list[Signal] = []
        for symbol in symbols:
            sig = self._signal_for(symbol)
            if sig:
                signals.append(sig)
        return signals

    def _signal_for(self, underlying: str) -> Signal | None:
        bars = self.market.bars(underlying, days=20)
        mom = momentum(bars, lookback=5)
        close = last_close(bars)
        quote = self.market.quote(underlying)
        price = quote.mid or quote.last or close
        if mom is None or price is None:
            return None
        if abs(mom) < self.threshold:
            return None

        direction = "long" if mom > 0 else "short"
        right = "call" if direction == "long" else "put"
        chain = self.market.option_chain(
            underlying,
            min_dte=self.settings.min_dte,
            max_dte=self.settings.max_dte,
            right=right,
            limit=100,
        )
        if not chain:
            return None

        scored: list[tuple[float, OptionSnapshot]] = []
        for contract in chain:
            snap = self.market.option_snapshot(contract.symbol, underlying_price=price)
            if snap.quote is None or snap.quote.mid is None:
                continue
            dist = abs(contract.strike - price) / price
            spread = snap.quote.spread_pct
            oi = contract.open_interest
            if spread is None or oi is None:
                continue
            score = -(dist * 10.0 + spread * 5.0) + min(oi, 5000) / 5000.0
            scored.append((score, snap))

        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        return Signal(
            underlying=underlying,
            direction=direction,
            confidence=min(0.85, 0.45 + abs(mom) * 20),
            thesis=(
                f"{underlying} 5-day momentum {mom:.2%} -> {right} "
                f"{best.contract.symbol} strike {best.contract.strike} exp {best.contract.expiration}"
            ),
            expected_edge=abs(mom),
            contract=best.contract.symbol,
            timestamp=datetime.now(timezone.utc),
            snapshot=best,
        )
