from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.app.config.logging import setup_logging
from backend.app.config.settings import Settings, get_settings
from backend.app.data.client import AlpacaClient
from backend.app.data.live_alpaca import LiveAlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.app.data.models import Signal, OptionSnapshot
from backend.app.database.db import Database
from backend.app.execution.engine import ExecutionEngine
from backend.app.risk.engine import RiskEngine
from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy
from backend.app.ai.supervisor import create_ai_supervisor
from backend.app.ai.base import AIInput, AIOutput


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
        self.ai_supervisor = create_ai_supervisor(self.settings)
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

        # Prepare market state for AI evaluation
        market_state = {
            "underlyings": self.settings.underlying_list,
            "account": account.model_dump(),
            "positions": [p.model_dump(mode="json") for p in positions],
        }

        signals = self.strategy.generate_signals(market_state)
        self.log.info("Generated %d signal(s)", len(signals))

        actions: list[dict[str, Any]] = []
        for signal in signals:
            duplicate = bool(signal.contract and self.db.has_open_order(signal.contract))

            # AI Supervisor Evaluation (Phase 6)
            ai_decision = None
            if self.ai_supervisor is not None:
                # Prepare input for AI supervisor
                ai_input = AIInput(
                    underlying=signal.underlying,
                    price=0.0,  # We'll need to get current price - for now use 0 as placeholder
                    features={},  # TODO: Extract actual features
                    signals=[signal],
                    options=[],  # TODO: Get options data
                    portfolio={"account": account.model_dump()},
                    risk={}
                )

                # Get AI decision
                ai_output = self.ai_supervisor.evaluate(ai_input)

                # Validate AI output
                if not self.ai_supervisor.validate_output(ai_output):
                    self.log.warning(
                        "AI output validation failed for %s. Defaulting to HOLD.",
                        signal.contract
                    )
                    ai_output = AIOutput(
                        decision="HOLD",
                        confidence=0.0,
                        contract=None,
                        thesis="AI output invalid - defaulting to HOLD for safety",
                        expected_horizon="N/A",
                        risk_factors=["AI validation error"],
                        invalidation_conditions=["AI system error"]
                    )

                ai_decision = ai_output
                self.log.info(
                    "AI decision for %s: %s (confidence: %.2f)",
                    signal.contract,
                    ai_output.decision,
                    ai_output.confidence
                )

                # If AI says HOLD, skip this signal
                if ai_output.decision == "HOLD":
                    record = {
                        "underlying": signal.underlying,
                        "contract": signal.contract,
                        "thesis": signal.thesis,
                        "approved": False,
                        "reasons": ["AI recommendation: HOLD"] + ai_output.risk_factors,
                    }

                    self.db.journal(
                        underlying=signal.underlying,
                        market_state={"account": account.model_dump()},
                        features={"confidence": signal.confidence, "direction": signal.direction},
                        strategy_signal=signal,
                        ai_decision=ai_output,
                        risk_decision={"approved": False, "reasons": ["AI recommendation: HOLD"]},
                        execution=None,
                        result={"rejected": True, "reasons": ["AI recommendation: HOLD"] + ai_output.risk_factors},
                    )
                    actions.append(record)
                    continue  # Skip to next signal

            # If AI is disabled or didn't say HOLD, proceed with original logic
            # (enhanced with AI input if available)
            effective_signal = signal
            if ai_decision is not None and ai_decision.decision != "HOLD":
                # Create a modified signal with AI inputs
                # For simplicity, we'll use the original signal but log that AI was consulted
                # In a more sophisticated implementation, we might adjust confidence, etc.
                pass

            decision = self.risk.evaluate(
                effective_signal,
                account,
                positions,
                trading_enabled=self.settings.trading_enabled,
                duplicate_open=duplicate,
            )
            record = {
                "underlying": effective_signal.underlying,
                "contract": effective_signal.contract,
                "thesis": effective_signal.thesis,
                "approved": decision.approved,
                "reasons": decision.reasons,
            }
            if decision.approved and submit:
                order = self.execution.execute(effective_signal, decision)
                position = self.client.get_position(effective_signal.contract) if effective_signal.contract else None
                record["order"] = order.model_dump(mode="json")
                record["position"] = position.model_dump(mode="json") if position else None
                self.log.info(
                    "ORDER submitted %s qty=%s status=%s alpaca_id=%s",
                    effective_signal.contract,
                    decision.qty,
                    order.status,
                    order.alpaca_id,
                )
            else:
                self.log.info(
                    "TRADE REJECTED %s reasons=%s",
                    effective_signal.contract,
                    "; ".join(decision.reasons),
                )

            self.db.journal(
                underlying=effective_signal.underlying,
                market_state={"account": account.model_dump()},
                features={"confidence": effective_signal.confidence, "direction": effective_signal.direction},
                strategy_signal=effective_signal,
                ai_decision=ai_decision if ai_decision is not None else AIOutput(
                    decision="HOLD", confidence=0.0, contract=None,
                    thesis="AI supervisor disabled", expected_horizon="N/A",
                    risk_factors=[], invalidation_conditions=[]
                ),
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
