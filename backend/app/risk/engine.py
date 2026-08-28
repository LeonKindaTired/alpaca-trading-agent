from __future__ import annotations

from backend.app.config.settings import Settings
from backend.app.data.models import (
    AccountSnapshot,
    PositionSnapshot,
    RiskDecision,
    Signal,
)


class RiskEngine:
    """Deterministic final authority. The LLM cannot bypass these checks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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
