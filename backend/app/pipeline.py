from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.config.logging import setup_logging
from backend.app.config.settings import Settings, get_settings
from backend.app.data.client import AlpacaClient
from backend.app.data.live_alpaca import LiveAlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.app.data.models import Signal
from backend.app.database.db import Database
from backend.app.execution.engine import ExecutionEngine
from backend.app.risk.engine import RiskEngine
from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy


@dataclass
class CycleResult:
    account: dict[str, Any]
    signals: list[Signal]
    actions: list[dict[str, Any]] = field(default_factory=list)


class TradingLoop:
    def __init__(self, client: AlpacaClient, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.db = Database(self.settings.database_path)
        self.market = MarketDataService(client)
        self.strategy = LiquidMomentumStrategy(self.market, self.settings)
        self.risk = RiskEngine(self.settings)
        self.execution = ExecutionEngine(client, self.db)
        self.log = setup_logging(self.settings.log_level)

    def run_once(self, *, submit: bool = True) -> CycleResult:
        account = self.client.get_account()
        positions = self.client.list_positions()
        self.log.info(
            "Account equity=%.2f buying_power=%.2f positions=%d trading_enabled=%s",
            account.equity,
            account.buying_power,
            len(positions),
            self.settings.trading_enabled,
        )

        signals = self.strategy.generate_signals({"underlyings": self.settings.underlying_list})
        self.log.info("Generated %d signal(s)", len(signals))

        actions: list[dict[str, Any]] = []
        for signal in signals:
            duplicate = bool(signal.contract and self.db.has_open_order(signal.contract))
            decision = self.risk.evaluate(
                signal,
                account,
                positions,
                trading_enabled=self.settings.trading_enabled,
                duplicate_open=duplicate,
            )
            record = {
                "underlying": signal.underlying,
                "contract": signal.contract,
                "thesis": signal.thesis,
                "approved": decision.approved,
                "reasons": decision.reasons,
            }
            if decision.approved and submit:
                order = self.execution.execute(signal, decision)
                position = self.client.get_position(signal.contract) if signal.contract else None
                record["order"] = order.model_dump(mode="json")
                record["position"] = position.model_dump(mode="json") if position else None
                self.log.info(
                    "ORDER submitted %s qty=%s status=%s alpaca_id=%s",
                    signal.contract,
                    decision.qty,
                    order.status,
                    order.alpaca_id,
                )
            else:
                self.log.info(
                    "TRADE REJECTED %s reasons=%s",
                    signal.contract,
                    "; ".join(decision.reasons),
                )

            self.db.journal(
                underlying=signal.underlying,
                market_state={"account": account.model_dump()},
                features={"confidence": signal.confidence, "direction": signal.direction},
                strategy_signal=signal,
                ai_decision="SKIPPED_PHASE1",
                risk_decision=decision,
                execution=record.get("order"),
                result=record.get("position") or {"rejected": not decision.approved, "reasons": decision.reasons},
            )
            actions.append(record)
            if decision.approved and submit:
                positions = self.client.list_positions()

        if not signals:
            self.db.journal(
                result={"note": "no signals this cycle"},
                risk_decision={"approved": False, "reasons": ["no quantitative opportunity"]},
            )

        return CycleResult(account=account.model_dump(), signals=signals, actions=actions)


def build_live_loop() -> TradingLoop:
    settings = get_settings()
    return TradingLoop(LiveAlpacaClient(settings), settings)
