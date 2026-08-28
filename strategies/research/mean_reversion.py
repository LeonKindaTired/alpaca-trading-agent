"""
Mean Reversion Strategy

Buys options when the underlying price deviates significantly from its mean,
expecting a reversion to the mean.

Uses Z-score: (price - SMA) / standard deviation of price.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.config.settings import Settings
from backend.app.data.market_data import MarketDataService
from backend.app.data.models import OptionSnapshot, Signal
from backend.app.features.engine import last_close, realized_volatility, sma
from backend.app.strategies.base import Strategy


class MeanReversionStrategy(Strategy):
    """Mean reversion strategy."""

    name = "mean_reversion"
    # Z-score threshold for signal generation
    z_threshold = 1.5
    # Lookback period for SMA and volatility
    lookback = 20
    # Minimum days to expiration for options
    min_dte = 3
    # Maximum days to expiration for options
    max_dte = 45

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
        # 1. Get recent bars for calculations
        bars = self.market.bars(underlying, days=self.lookback + 5)
        if len(bars) < self.lookback + 1:
            return None

        # 2. Calculate SMA and standard deviation of price
        sma_val = sma(bars, lookback=self.lookback)
        if sma_val is None:
            return None

        # Calculate standard deviation of closing prices
        closes = [bar.close for bar in bars[-self.lookback:] if bar.close is not None]
        if len(closes) < self.lookback:
            return None
        mean_price = sum(closes) / self.lookback
        variance = sum((c - mean_price) ** 2 for c in closes) / self.lookback
        std_price = variance ** 0.5
        if std_price == 0:
            return None

        # 3. Get latest price
        last_price = last_close(bars)
        if last_price is None:
            return None

        # 4. Calculate Z-score
        z_score = (last_price - mean_price) / std_price

        # 5. Determine signal based on Z-score
        # If Z-score < -threshold: price is below mean -> expect reversion up -> buy call
        # If Z-score > threshold: price is above mean -> expect reversion down -> buy put
        if abs(z_score) < self.z_threshold:
            return None  # Not significant enough

        if z_score < -self.z_threshold:
            # Oversold: expect price to rise -> buy call
            direction = "long"
            right = "call"
        else:
            # Overbought: expect price to fall -> buy put
            direction = "short"
            right = "put"

        # 6. Get options chain for the underlying
        chain = self.market.option_chain(
            underlying,
            min_dte=self.min_dte,
            max_dte=self.max_dte,
            right=right,
            limit=50,
        )
        if not chain:
            return None

        # 7. Select the best option (we can reuse logic from liquid_momentum for consistency)
        scored: list[tuple[float, OptionSnapshot]] = []
        for contract in chain:
            snap = self.market.option_snapshot(contract.symbol, underlying_price=last_price)
            if snap.quote is None or snap.quote.mid is None:
                continue
            dist = abs(contract.strike - last_price) / last_price
            spread = snap.quote.spread_pct
            oi = contract.open_interest
            vol = contract.volume
            if spread is None or oi is None:
                continue
            if spread > self.settings.max_bid_ask_spread:
                continue
            if oi < self.settings.min_open_interest:
                continue
            if vol is not None and vol < self.settings.min_option_volume:
                continue
            # Score: we want near-the-money (low dist), tight spread (low spread), high OI
            score = -(dist * 10.0 + spread * 5.0) + min(oi, 5000) / 5000.0
            scored.append((score, snap))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_snap = scored[0]

        # Build thesis
        thesis = (
            f"{underlying} price={last_price:.2f} SMA={sma_val:.2f} Z={z_score:.2f} "
            f"→ {right} {best_snap.contract.symbol} strike {best_snap.contract.strike} "
            f"exp {best_snap.contract.expiration}"
        )

        return Signal(
            underlying=underlying,
            direction=direction,
            confidence=min(0.85, 0.45 + abs(z_score) * 0.1),  # Scale confidence by Z-score
            thesis=thesis,
            expected_edge=abs(z_score),  # The Z-score edge
            contract=best_snap.contract.symbol,
            timestamp=datetime.now(timezone.utc),
            snapshot=best_snap,
        )