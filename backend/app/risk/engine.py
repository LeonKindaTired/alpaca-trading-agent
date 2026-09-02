from __future__ import annotations

from backend.app.config.settings import Settings
from backend.app.data.models import (
    AccountSnapshot,
    PositionSnapshot,
    RiskDecision,
    Signal,
)
from backend.app.data.market_data import MarketDataService
from backend.app.features.engine import returns
import math


class RiskEngine:
    """Deterministic final authority. The LLM cannot bypass these checks."""

    def __init__(self, settings: Settings, market_data: MarketDataService) -> None:
        self.settings = settings
        self.market_data = market_data

    def evaluate(
        self,
        signal: Signal,
        account: AccountSnapshot,
        positions: list[PositionSnapshot],
        *,
        trading_enabled: bool | None = None,
        duplicate_open: bool = False,
    ) -> RiskDecision:
        reasons: list[str] = []
        enabled = self.settings.trading_enabled if trading_enabled is None else trading_enabled

        if not enabled:
            reasons.append("Kill switch TRADING_ENABLED=false")
        if account.trading_blocked:
            reasons.append("Alpaca trading_blocked=true")

        snap = signal.snapshot
        if snap is None or snap.quote is None:
            reasons.append("Missing option quote; refusing to invent prices")
            return RiskDecision(approved=False, reasons=reasons, qty=0)

        quote = snap.quote
        spread = quote.spread_pct
        mid = quote.mid
        if spread is None or mid is None:
            reasons.append("Bid/ask incomplete; missing data is not treated as valid")
        elif spread > self.settings.max_bid_ask_spread:
            reasons.append(
                f"Bid/ask spread too wide: {spread:.1%} > max {self.settings.max_bid_ask_spread:.1%}"
            )

        dte = snap.dte
        if dte is None:
            reasons.append("Missing expiration")
        else:
            if dte < self.settings.min_dte:
                reasons.append(f"DTE {dte} below minimum {self.settings.min_dte}")
            if dte > self.settings.max_dte:
                reasons.append(f"DTE {dte} above maximum {self.settings.max_dte}")

        oi = snap.contract.open_interest
        vol = snap.contract.volume
        if oi is None:
            reasons.append("Open interest missing")
        elif oi < self.settings.min_open_interest:
            reasons.append(f"Open interest {oi} < min {self.settings.min_open_interest}")
        if vol is not None and vol < self.settings.min_option_volume:
            reasons.append(f"Volume {vol} < min {self.settings.min_option_volume}")

        if len(positions) >= self.settings.max_positions:
            reasons.append(
                f"Max simultaneous positions {self.settings.max_positions} already open"
            )

        same_underlying = [
            p for p in positions if signal.underlying in p.symbol or p.symbol.startswith(signal.underlying)
        ]
        if same_underlying:
            reasons.append(f"Underlying concentration: already holding {signal.underlying}")

        if duplicate_open:
            reasons.append(f"Duplicate order prevention: open order exists for {signal.contract}")

        # Check correlation and concentration limits
        self._check_correlation_and_concentration(signal, positions, reasons)

        if mid is None or mid <= 0:
            return RiskDecision(approved=False, reasons=reasons or ["No valid mid price"], qty=0)

        # Options multiplier is 100. Risk a small fraction of equity on premium paid.
        premium = mid * 100
        risk_budget = account.equity * self.settings.max_risk_per_trade
        qty = int(risk_budget // premium)
        if qty < 1:
            qty = 1
            if premium > risk_budget * 1.5:
                reasons.append(
                    f"Premium ${premium:.2f} exceeds max risk per trade ${risk_budget:.2f}"
                )

        exposure = sum(abs(p.market_value or 0) for p in positions)
        new_exposure = exposure + premium * qty
        if account.portfolio_value > 0 and new_exposure / account.portfolio_value > self.settings.max_portfolio_exposure:
            reasons.append("Proposed exposure exceeds MAX_PORTFOLIO_EXPOSURE")

        if account.buying_power < premium * qty:
            reasons.append("Insufficient buying power")

        if reasons:
            return RiskDecision(approved=False, reasons=reasons, qty=0, details={"spread": spread, "mid": mid})

        return RiskDecision(
            approved=True,
            reasons=["All deterministic risk checks passed"],
            qty=float(qty),
            max_loss=premium * qty,
            details={"spread": spread, "mid": mid, "premium": premium},
        )

    def _check_correlation_and_concentration(self, signal: Signal, positions: list[PositionSnapshot], reasons: list[str]) -> None:
        """Check correlation and concentration limits"""
        # Count positions in same direction
        same_direction_positions = [
            p for p in positions
            if ((signal.direction == "long" and p.side.lower() in ["buy", "long"]) or
                (signal.direction == "short" and p.side.lower() in ["sell", "short"]))
        ]

        if len(same_direction_positions) >= self.settings.max_same_direction:
            reasons.append(
                f"Max same-direction positions exceeded: {len(same_direction_positions)} >= {self.settings.max_same_direction}"
            )
            return

        # Count correlated positions (simplified: same underlying or sector)
        # For simplicity, we'll consider positions with same underlying as correlated
        correlated_positions = [
            p for p in positions
            if signal.underlying in p.symbol or p.symbol.startswith(signal.underlying)
        ]

        if len(correlated_positions) >= self.settings.max_correlated_positions:
            reasons.append(
                f"Max correlated positions exceeded: {len(correlated_positions)} >= {self.settings.max_correlated_positions}"
            )
            return

        # Check sector concentration (simplified: we don't have sector data, so skip for now)
        # In a real implementation, we would map underlyings to sectors and check concentration

        # Check underlying concentration (already handled in the main evaluate method)
        # but we'll keep it here for completeness
        underlying_positions = [
            p for p in positions
            if signal.underlying in p.symbol or p.symbol.startswith(signal.underlying)
        ]

        if underlying_positions:
            reasons.append(f"Underlying concentration: already holding {signal.underlying}")
