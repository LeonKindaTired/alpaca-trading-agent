from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data import DataFeed
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import (
    OptionLatestQuoteRequest,
    OptionSnapshotRequest,
    StockBarsRequest,
    StockLatestQuoteRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    AssetStatus,
    ContractType,
    OrderSide,
    QueryOrderStatus,
    TimeInForce,
)
from alpaca.trading.requests import GetOptionContractsRequest, GetOrdersRequest, MarketOrderRequest

from backend.app.config.settings import Settings
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


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _order_side(side: str) -> OrderSide:
    return OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL


class LiveAlpacaClient(AlpacaClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
        if not settings.alpaca_paper:
            raise RuntimeError("Live trading is blocked. Set ALPACA_PAPER=true.")

        self.settings = settings
        key = settings.alpaca_api_key
        secret = settings.alpaca_secret_key
        self.trading = TradingClient(api_key=key, secret_key=secret, paper=True)
        self.stocks = StockHistoricalDataClient(api_key=key, secret_key=secret)
        self.options = OptionHistoricalDataClient(api_key=key, secret_key=secret)

    def get_account(self) -> AccountSnapshot:
        acc = self.trading.get_account()
        equity = _f(acc.equity)
        cash = _f(acc.cash)
        buying_power = _f(acc.buying_power)
        portfolio_value = _f(getattr(acc, "portfolio_value", None)) or equity
        if equity is None or cash is None or buying_power is None or portfolio_value is None:
            raise RuntimeError("Account fields missing from Alpaca response")
        return AccountSnapshot(
            equity=equity,
            cash=cash,
            buying_power=buying_power,
            portfolio_value=portfolio_value,
            last_equity=_f(getattr(acc, "last_equity", None)),
            status=str(getattr(acc, "status", None)),
            options_approved_level=_i(getattr(acc, "options_approved_level", None)),
            trading_blocked=bool(getattr(acc, "trading_blocked", False)),
        )

    def get_latest_quote(self, symbol: str) -> Quote:
        req = StockLatestQuoteRequest(symbol_or_symbols=symbol, feed=DataFeed.IEX)
        quotes = self.stocks.get_stock_latest_quote(req)
        raw = quotes[symbol]
        return Quote(
            symbol=symbol,
            bid=_f(getattr(raw, "bid_price", None)),
            ask=_f(getattr(raw, "ask_price", None)),
            timestamp=getattr(raw, "timestamp", None),
        )

    def get_bars(self, symbol: str, *, days: int = 30) -> list[Bar]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days + 5)
        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=DataFeed.IEX,
        )
        bars = self.stocks.get_stock_bars(req)
        frames = bars[symbol]
        out: list[Bar] = []
        for bar in frames:
            close = _f(bar.close)
            open_ = _f(bar.open)
            high = _f(bar.high)
            low = _f(bar.low)
            if close is None or open_ is None or high is None or low is None:
                continue
            out.append(
                Bar(
                    symbol=symbol,
                    timestamp=bar.timestamp,
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    volume=_f(bar.volume),
                )
            )
        return out[-days:]

    def get_option_contracts(
        self,
        underlying: str,
        *,
        expiration_gte: date | None = None,
        expiration_lte: date | None = None,
        right: str | None = None,
        limit: int = 100,
    ) -> list[OptionContract]:
        contract_type = None
        if right:
            contract_type = ContractType.CALL if right.lower() == "call" else ContractType.PUT
        req = GetOptionContractsRequest(
            underlying_symbols=[underlying],
            status=AssetStatus.ACTIVE,
            expiration_date_gte=expiration_gte,
            expiration_date_lte=expiration_lte,
            type=contract_type,
            limit=limit,
        )
        res = self.trading.get_option_contracts(req)
        contracts = []
        for c in res.option_contracts or []:
            strike = _f(c.strike_price)
            exp = c.expiration_date
            if strike is None or exp is None or not c.symbol:
                continue
            if isinstance(exp, str):
                exp = date.fromisoformat(exp)
            right_val = str(c.type).lower()
            if "put" in right_val:
                opt_right = OptionRight.PUT
            else:
                opt_right = OptionRight.CALL
            contracts.append(
                OptionContract(
                    symbol=c.symbol,
                    underlying=underlying,
                    expiration=exp,
                    strike=strike,
                    right=opt_right,
                    tradable=getattr(c, "tradable", None),
                    status=str(getattr(c, "status", None)),
                    open_interest=_i(getattr(c, "open_interest", None)),
                )
            )
        return contracts

    def get_option_contract(self, symbol: str) -> OptionContract:
        c = self.trading.get_option_contract(symbol)
        strike = _f(c.strike_price)
        exp = c.expiration_date
        if strike is None or exp is None:
            raise RuntimeError(f"Incomplete option contract for {symbol}")
        if isinstance(exp, str):
            exp = date.fromisoformat(exp)
        right_val = str(c.type).lower()
        opt_right = OptionRight.PUT if "put" in right_val else OptionRight.CALL
        return OptionContract(
            symbol=c.symbol,
            underlying=c.underlying_symbol,
            expiration=exp,
            strike=strike,
            right=opt_right,
            tradable=getattr(c, "tradable", None),
            status=str(getattr(c, "status", None)),
            open_interest=_i(getattr(c, "open_interest", None)),
        )

    def get_option_snapshot(
        self, symbol: str, *, underlying_price: float | None = None
    ) -> OptionSnapshot:
        contract = self.get_option_contract(symbol)
        quote: Quote | None = None
        iv: float | None = None
        greeks: Greeks | None = None
        try:
            snap_req = OptionSnapshotRequest(symbol_or_symbols=symbol, feed=DataFeed.IEX)
            snaps = self.options.get_option_snapshot(snap_req)
            raw = snaps[symbol]
            latest_quote = getattr(raw, "latest_quote", None)
            if latest_quote is not None:
                quote = Quote(
                    symbol=symbol,
                    bid=_f(getattr(latest_quote, "bid_price", None)),
                    ask=_f(getattr(latest_quote, "ask_price", None)),
                    timestamp=getattr(latest_quote, "timestamp", None),
                )
            iv = _f(getattr(raw, "implied_volatility", None))
            g = getattr(raw, "greeks", None)
            if g is not None:
                greeks = Greeks(
                    delta=_f(getattr(g, "delta", None)),
                    gamma=_f(getattr(g, "gamma", None)),
                    theta=_f(getattr(g, "theta", None)),
                    vega=_f(getattr(g, "vega", None)),
                )
        except Exception:
            try:
                qreq = OptionLatestQuoteRequest(symbol_or_symbols=symbol, feed=DataFeed.IEX)
                qmap = self.options.get_option_latest_quote(qreq)
                q = qmap[symbol]
                quote = Quote(
                    symbol=symbol,
                    bid=_f(getattr(q, "bid_price", None)),
                    ask=_f(getattr(q, "ask_price", None)),
                    timestamp=getattr(q, "timestamp", None),
                )
            except Exception:
                quote = None

        return OptionSnapshot(
            contract=contract,
            quote=quote,
            implied_volatility=iv,
            greeks=greeks,
            underlying_price=underlying_price,
        )

    def submit_market_order(
        self, *, symbol: str, qty: float, side: str, internal_id: str
    ) -> OrderRecord:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=_order_side(side),
            time_in_force=TimeInForce.DAY,
            client_order_id=internal_id,
        )
        order = self.trading.submit_order(req)
        return _map_order(order, internal_id)

    def get_order(self, alpaca_id: str) -> OrderRecord:
        order = self.trading.get_order_by_id(alpaca_id)
        return _map_order(order, getattr(order, "client_order_id", "") or "")

    def list_orders(self, *, status: str = "all") -> list[OrderRecord]:
        mapping = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL,
        }
        req = GetOrdersRequest(status=mapping.get(status, QueryOrderStatus.ALL))
        orders = self.trading.get_orders(filter=req)
        return [_map_order(o, getattr(o, "client_order_id", "") or "") for o in orders]

    def cancel_order(self, alpaca_id: str) -> None:
        self.trading.cancel_order_by_id(alpaca_id)

    def list_positions(self) -> list[PositionSnapshot]:
        return [_map_position(p) for p in self.trading.get_all_positions()]

    def get_position(self, symbol: str) -> PositionSnapshot | None:
        try:
            return _map_position(self.trading.get_open_position(symbol))
        except Exception:
            return None

    def close_position(self, symbol: str) -> Any:
        return self.trading.close_position(symbol)


def _map_order(order: Any, internal_id: str) -> OrderRecord:
    return OrderRecord(
        internal_id=internal_id or str(getattr(order, "client_order_id", "") or ""),
        alpaca_id=str(order.id) if getattr(order, "id", None) else None,
        symbol=str(order.symbol),
        side=str(order.side),
        qty=float(order.qty) if order.qty is not None else 0.0,
        status=str(order.status),
        filled_qty=_f(getattr(order, "filled_qty", None)),
        filled_avg_price=_f(getattr(order, "filled_avg_price", None)),
        raw={"id": str(getattr(order, "id", "")), "status": str(getattr(order, "status", ""))},
    )


def _map_position(pos: Any) -> PositionSnapshot:
    return PositionSnapshot(
        symbol=str(pos.symbol),
        qty=float(pos.qty),
        side=str(pos.side),
        avg_entry_price=_f(getattr(pos, "avg_entry_price", None)),
        current_price=_f(getattr(pos, "current_price", None)),
        market_value=_f(getattr(pos, "market_value", None)),
        unrealized_pl=_f(getattr(pos, "unrealized_pl", None)),
        asset_class=str(getattr(pos, "asset_class", "")),
    )
