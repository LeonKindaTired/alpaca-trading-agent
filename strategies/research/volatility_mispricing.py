"""
Volatility Mispricing Strategy

Buys options when implied volatility is significantly below realized volatility,
indicating the option may be undervalued.

Direction is determined by short-term momentum (call for upside momentum, put for downside).
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.config.settings import Settings
from backend.app.data.market_data import MarketDataService
from backend.app.data.models import OptionSnapshot, Signal
from backend.app.features.engine import momentum, realized_volatility
from backend.app.strategies.base import Strategy


class VolatilityMispricingStrategy(Strategy):
    """Volatility mispricing strategy."""

    name = "volatility_mispricing"
    # Threshold for volatility difference (in volatility points, e.g., 0.05 = 5%)
    vol_threshold = 0.05
    # Momentum lookback for directional bias
    momentum_lookback = 5
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
        # 1. Calculate realized volatility of the underlying
        bars = self.market.bars(underlying, days=30)  # Use enough data for RV
        rv = realized_volatility(bars, lookback=20)
        if rv is None:
            return None

        # 2. Get directional bias from momentum
        mom = momentum(bars, lookback=self.momentum_lookback)
        if mom is None:
            return None

        # Determine option type based on momentum
        direction = "long" if mom > 0 else "short"
        right = "call" if direction == "long" else "put"

        # 3. Get options chain for the underlying
        chain = self.market.option_chain(
            underlying,
            min_dte=self.min_dte,
            max_dte=self.max_dte,
            right=right,
            limit=50,  # Get a reasonable number of contracts to find the best one
        )
        if not chain:
            return None

        # 4. For each option, get implied volatility and compare to realized volatility
        scored: list[tuple[float, OptionSnapshot]] = []
        for contract in chain:
            snap = self.market.option_snapshot(contract.symbol, underlying_price=None)
            if snap.quote is None or snap.quote.mid is None:
                continue
            iv = snap.implied_volatility
            if iv is None:
                continue

            # Calculate volatility difference: IV - RV
            vol_diff = iv - rv
            # We are looking for undervalued options: IV < RV (negative diff)
            if vol_diff >= -self.vol_threshold:
                # Not undervalued enough
                continue

            # Additional filtering: we prefer options with reasonable bid/ask spread and open interest
            quote = snap.quote
            spread = quote.spread_pct
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

            # Score based on how undervalued the option is (more negative is better)
            # We also consider liquidity (higher OI and volume is better)
            score = vol_diff  # More negative is better
            # Adjust score by liquidity (normalize OI and volume to [0,1] range, but we don't have max)
            # For simplicity, we just use the volatility difference as the primary score.
            scored.append((score, snap))

        if not scored:
            return None

        # Sort by score (most negative first, i.e., most undervalued)
        scored.sort(key=lambda x: x[0])
        best_score, best_snap = scored[0]

        # Build thesis
        thesis = (
            f"{underlying} IV={best_snap.implied_volatility:.1%} RV={rv:.1%} "
            f"diff={best_score:.1%} -> {right} {best_snap.contract.symbol} "
            f"strike {best_snap.contract.strike} exp {best_snap.contract.expiration}"
        )

        return Signal(
            underlying=underlying,
            direction=direction,
            confidence=min(0.85, 0.45 + abs(mom) * 20),  # Similar to liquid_momentum
            thesis=thesis,
            expected_edge=abs(best_score),  # The volatility edge
            contract=best_snap.contract.symbol,
            timestamp=datetime.now(timezone.utc),
            snapshot=best_snap,
        )