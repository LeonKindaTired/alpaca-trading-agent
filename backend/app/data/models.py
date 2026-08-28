from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class MissingDataError(ValueError):
    """Raised when required market data is absent. Never coerce missing values to 0."""


class OptionRight(str, Enum):
    CALL = "call"
    PUT = "put"


class Quote(BaseModel):
    symbol: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    timestamp: datetime | None = None

    @model_validator(mode="after")
    def _reject_silent_zeros_as_valid(self) -> "Quote":
        # Zero is allowed only if explicitly present; None stays None.
        return self

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2.0

    @property
    def spread_pct(self) -> float | None:
        mid = self.mid
        if mid is None or mid <= 0 or self.bid is None or self.ask is None:
            return None
        return (self.ask - self.bid) / mid


class Bar(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class OptionContract(BaseModel):
    symbol: str
    underlying: str
    expiration: date
    strike: float
    right: OptionRight
    tradable: bool | None = None
    status: str | None = None
    open_interest: int | None = None
    volume: int | None = None


class Greeks(BaseModel):
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None


class OptionSnapshot(BaseModel):
    contract: OptionContract
    quote: Quote | None = None
    implied_volatility: float | None = None
    greeks: Greeks | None = None
    underlying_price: float | None = None

    @property
    def dte(self) -> int | None:
        if self.contract.expiration is None:
            return None
        today = date.today()
        return (self.contract.expiration - today).days

    @property
    def distance_from_strike(self) -> float | None:
        if self.underlying_price is None:
            return None
        return self.underlying_price - self.contract.strike


class AccountSnapshot(BaseModel):
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    last_equity: float | None = None
    status: str | None = None
    options_approved_level: int | None = None
    trading_blocked: bool = False


class PositionSnapshot(BaseModel):
    symbol: str
    qty: float
    side: str
    avg_entry_price: float | None = None
    current_price: float | None = None
    market_value: float | None = None
    unrealized_pl: float | None = None
    asset_class: str | None = None


class OrderRecord(BaseModel):
    internal_id: str
    alpaca_id: str | None = None
    symbol: str
    side: str
    qty: float
    status: str
    filled_qty: float | None = None
    filled_avg_price: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Signal(BaseModel):
    underlying: str
    direction: str
    confidence: float
    thesis: str
    expected_edge: float | None = None
    contract: str | None = None
    timestamp: datetime
    snapshot: OptionSnapshot | None = None


class RiskDecision(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    qty: float = 0
    max_loss: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
