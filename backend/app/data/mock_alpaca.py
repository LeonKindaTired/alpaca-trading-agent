from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from backend.app.data.client import AlpacaClient
from backend.app.data.models import (
    AccountSnapshot,
    Bar,
    Greeks,
    OptionContract,
    OptionRight,
    OptionSnapshot,
    OrderRecord,
    PositionSnapshot,
    Quote,
)


class MockAlpacaClient(AlpacaClient):
    """In-memory Alpaca stand-in. Unit tests must never hit the network."""

    def __init__(self) -> None:
        self.account = AccountSnapshot(
            equity=100_000,
            cash=100_000,
            buying_power=200_000,
            portfolio_value=100_000,
            last_equity=100_000,
            status="ACTIVE",
            options_approved_level=2,
            trading_blocked=False,
        )
        self._orders: dict[str, OrderRecord] = {}
        self._positions: dict[str, PositionSnapshot] = {}
        self.submitted: list[OrderRecord] = []
        today = date.today()
        self._expiry = today + timedelta(days=21)
        self._spy_price = 560.0
        self.fail_next_order = False

    def get_account(self) -> AccountSnapshot:
        return self.account

    def get_latest_quote(self, symbol: str) -> Quote:
        px = self._spy_price if symbol == "SPY" else 480.0
        return Quote(
            symbol=symbol,
            bid=px - 0.01,
            ask=px + 0.01,
            last=px,
            timestamp=datetime.now(timezone.utc),
        )

    def get_bars(self, symbol: str, *, days: int = 30) -> list[Bar]:
        px = self._spy_price if symbol == "SPY" else 480.0
        bars: list[Bar] = []
        for i in range(days):
            close = px * (1 + 0.04 * i / max(days - 1, 1))
            ts = datetime.now(timezone.utc) - timedelta(days=days - i)
            bars.append(
                Bar(
                    symbol=symbol,
                    timestamp=ts,
                    open=close * 0.999,
                    high=close * 1.005,
                    low=close * 0.995,
                    close=close,
                    volume=80_000_000,
                )
            )
        return bars

    def get_option_contracts(
        self,
        underlying: str,
        *,
        expiration_gte: date | None = None,
        expiration_lte: date | None = None,
        right: str | None = None,
        limit: int = 100,
    ) -> list[OptionContract]:
        px = self._spy_price if underlying == "SPY" else 480.0
        opt_right = OptionRight.CALL if (right or "call").lower() == "call" else OptionRight.PUT
        contracts = []
        for offset in (-10, -5, 0, 5, 10):
            strike = round(px + offset, 0)
            contracts.append(
                OptionContract(
                    symbol=f"{underlying}{self._expiry.strftime('%y%m%d')}{'C' if opt_right == OptionRight.CALL else 'P'}{int(strike * 1000):08d}",
                    underlying=underlying,
                    expiration=self._expiry,
                    strike=strike,
                    right=opt_right,
                    tradable=True,
                    status="active",
                    open_interest=2500,
                    volume=400,
                )
            )
        return contracts[:limit]

    def get_option_contract(self, symbol: str) -> OptionContract:
        right = OptionRight.PUT if "P00" in symbol or "P0" in symbol[-9:] else OptionRight.CALL
        # OCC: C/P then 8-digit strike
        flag = "C" if "C" in symbol[-9:] else "P"
        right = OptionRight.CALL if flag == "C" else OptionRight.PUT
        strike_digits = symbol[-8:]
        strike = int(strike_digits) / 1000.0
        underlying = "SPY" if symbol.startswith("SPY") else symbol[:3]
        return OptionContract(
            symbol=symbol,
            underlying=underlying,
            expiration=self._expiry,
            strike=strike,
            right=right,
            tradable=True,
            status="active",
            open_interest=2500,
            volume=400,
        )

    def get_option_snapshot(
        self, symbol: str, *, underlying_price: float | None = None
    ) -> OptionSnapshot:
        contract = self.get_option_contract(symbol)
        mid = 4.50
        return OptionSnapshot(
            contract=contract,
            quote=Quote(
                symbol=symbol,
                bid=mid - 0.05,
                ask=mid + 0.05,
                last=mid,
                timestamp=datetime.now(timezone.utc),
            ),
            implied_volatility=0.18,
            greeks=Greeks(delta=0.52 if contract.right == OptionRight.CALL else -0.48, gamma=0.04, theta=-0.03, vega=0.12),
            underlying_price=underlying_price or self._spy_price,
        )

    def submit_market_order(
        self, *, symbol: str, qty: float, side: str, internal_id: str
    ) -> OrderRecord:
        if self.fail_next_order:
            self.fail_next_order = False
            raise RuntimeError("mock order rejected")
        alpaca_id = str(uuid4())
        rec = OrderRecord(
            internal_id=internal_id,
            alpaca_id=alpaca_id,
            symbol=symbol,
            side=side,
            qty=qty,
            status="filled",
            filled_qty=qty,
            filled_avg_price=4.50,
        )
        self._orders[alpaca_id] = rec
        self.submitted.append(rec)
        signed_qty = qty if side.lower() == "buy" else -qty
        existing = self._positions.get(symbol)
        if existing:
            existing.qty += signed_qty
        else:
            self._positions[symbol] = PositionSnapshot(
                symbol=symbol,
                qty=signed_qty,
                side="long" if signed_qty > 0 else "short",
                avg_entry_price=4.50,
                current_price=4.50,
                market_value=4.50 * 100 * abs(signed_qty),
                unrealized_pl=0.0,
                asset_class="us_option",
            )
        return rec

    def get_order(self, alpaca_id: str) -> OrderRecord:
        return self._orders[alpaca_id]

    def list_orders(self, *, status: str = "all") -> list[OrderRecord]:
        return list(self._orders.values())

    def cancel_order(self, alpaca_id: str) -> None:
        if alpaca_id in self._orders:
            self._orders[alpaca_id].status = "canceled"

    def list_positions(self) -> list[PositionSnapshot]:
        return [p for p in self._positions.values() if p.qty != 0]

    def get_position(self, symbol: str) -> PositionSnapshot | None:
        pos = self._positions.get(symbol)
        if pos is None or pos.qty == 0:
            return None
        return pos

    def close_position(self, symbol: str) -> dict:
        if symbol in self._positions:
            self._positions[symbol].qty = 0
        return {"symbol": symbol, "status": "closed"}
