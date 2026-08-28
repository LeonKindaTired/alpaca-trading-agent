from __future__ import annotations

from datetime import date, timedelta

from backend.app.data.client import AlpacaClient
from backend.app.data.models import Bar, OptionContract, OptionSnapshot, Quote


class MarketDataService:
    def __init__(self, client: AlpacaClient) -> None:
        self.client = client

    def quote(self, symbol: str) -> Quote:
        return self.client.get_latest_quote(symbol)

    def bars(self, symbol: str, days: int = 30) -> list[Bar]:
        return self.client.get_bars(symbol, days=days)

    def option_chain(
        self,
        underlying: str,
        *,
        min_dte: int,
        max_dte: int,
        right: str,
        limit: int = 100,
    ) -> list[OptionContract]:
        today = date.today()
        return self.client.get_option_contracts(
            underlying,
            expiration_gte=today + timedelta(days=min_dte),
            expiration_lte=today + timedelta(days=max_dte),
            right=right,
            limit=limit,
        )

    def option_snapshot(self, symbol: str, *, underlying_price: float | None) -> OptionSnapshot:
        return self.client.get_option_snapshot(symbol, underlying_price=underlying_price)
