from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

from backend.app.data.models import (
    AccountSnapshot,
    Bar,
    OptionContract,
    OptionSnapshot,
    OrderRecord,
    PositionSnapshot,
    Quote,
)


class AlpacaClient(ABC):
    """Trading + market-data adapter. Strategies never call Alpaca SDK types directly."""

    @abstractmethod
    def get_account(self) -> AccountSnapshot: ...

    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    def get_bars(self, symbol: str, *, days: int = 30) -> list[Bar]: ...

    @abstractmethod
    def get_option_contracts(
        self,
        underlying: str,
        *,
        expiration_gte: date | None = None,
        expiration_lte: date | None = None,
        right: str | None = None,
        limit: int = 100,
    ) -> list[OptionContract]: ...

    @abstractmethod
    def get_option_contract(self, symbol: str) -> OptionContract: ...

    @abstractmethod
    def get_option_snapshot(
        self, symbol: str, *, underlying_price: float | None = None
    ) -> OptionSnapshot: ...

    @abstractmethod
    def submit_market_order(
        self, *, symbol: str, qty: float, side: str, internal_id: str
    ) -> OrderRecord: ...

    @abstractmethod
    def get_order(self, alpaca_id: str) -> OrderRecord: ...

    @abstractmethod
    def list_orders(self, *, status: str = "all") -> list[OrderRecord]: ...

    @abstractmethod
    def cancel_order(self, alpaca_id: str) -> None: ...

    @abstractmethod
    def list_positions(self) -> list[PositionSnapshot]: ...

    @abstractmethod
    def get_position(self, symbol: str) -> PositionSnapshot | None: ...

    @abstractmethod
    def close_position(self, symbol: str) -> Any: ...
