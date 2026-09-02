from __future__ import annotations

import datetime
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
from backend.app.strategies.multi_factor_strategy import MultiFactorStrategy
from backend.app.ai.supervisor import create_ai_supervisor
from backend.app.ai.base import AIInput, AIOutput
import json


@dataclass
class CycleResult:
    account: dict[str, Any]
    signals: list[Signal]
    actions: list[dict[str, Any]] = field(default_factory=list)


class TradingLoop:
    def __init__(self, client: AlpacaClient, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.db = Database(self.settings.database_path, self.settings)
        self.market = MarketDataService(client)
        self.strategy = MultiFactorStrategy(self.market, self.settings)
        self.risk = RiskEngine(self.settings, self.market)
        self.execution = ExecutionEngine(client, self.db)
        # AI Supervisor: only create if use_ai_supervisor is True
        self.ai_supervisor = create_ai_supervisor(self.settings) if self.settings.use_ai_supervisor else None
        self.log = setup_logging(self.settings.log_level)
        # Position metadata: contract -> {entry_time, entry_price, thesis, invalidation_conditions, quantity, side}
        self.position_metadata: dict[str, dict] = {}
        self.max_position_hours = getattr(self.settings, 'max_position_hours', 24.0)
        # Shutdown tracking
        self._daily_starting_equity: float | None = None
        self._daily_start_date: datetime.date | None = None
        self._peak_equity: float | None = None
        self._consecutive_failures: int = 0
        self._shutdown_reason: str | None = None
        self._trading_halted: bool = False  # if True, no new positions but still monitor existing

        # For dashboard enhancements
        self._latest_signals: list = []
        self._market_regime: str = "UNKNOWN"
        self._regime_confidence: float = 0.0
        self._candidates_count: int = 0
        self._qualified_count: int = 0

    def _update_position_metadata(self, contract: str, order, position, signal, ai_decision):
        """Store metadata for a newly opened position."""
        entry_price = None
        if order and hasattr(order, 'filled_avg_price') and order.filled_avg_price is not None:
            entry_price = float(order.filled_avg_price)
        elif position and hasattr(position, 'avg_entry_price') and position.avg_entry_price is not None:
            entry_price = float(position.avg_entry_price)
        else:
            # Fallback to current mid price
            snap = self.market.option_snapshot(contract)
            if snap and snap.quote and snap.quote.mid is not None:
                entry_price = float(snap.quote.mid)
            else:
                entry_price = 0.0

        metadata = {
            'entry_time': datetime.datetime.now(datetime.timezone.utc),
            'entry_price': entry_price,
            'thesis': getattr(signal, 'thesis', ''),
            'invalidation_conditions': getattr(ai_decision, 'invalidation_conditions', []) if ai_decision else [],
            'quantity': float(getattr(position, 'qty', 0)) if position else 0.0,
            'side': getattr(position, 'side', 'buy') if position else 'buy',
        }
        self.position_metadata[contract] = metadata
        self.log.info(
            "Stored metadata for position %s: entry_price=%.4f, thesis=%s",
            contract, entry_price, metadata['thesis'][:50]
        )

    def _remove_position_metadata(self, contract: str):
        """Remove metadata when position is closed."""
        if contract in self.position_metadata:
            del self.position_metadata[contract]
            self.log.info("Removed metadata for position %s", contract)

    def _evaluate_exit_conditions(self, contract: str, position, metadata: dict) -> tuple[bool, str]:
        """Evaluate whether to exit a position based on stop loss, time, and invalidation conditions.
        Returns (should_exit, reason).
        """
        if not position or not metadata:
            return False, ""

        # Get current option price
        snap = self.market.option_snapshot(contract)
        if not snap or not snap.quote or snap.quote.mid is None:
            return False, "Unable to get current quote"

        current_price = float(snap.quote.mid)
        entry_price = float(metadata['entry_price'])
        qty = float(metadata['quantity'])

        # Stop loss: exit if option price drops below 50% of entry price
        if entry_price > 0 and current_price <= entry_price * 0.5:
            return True, f"Stop loss triggered: {current_price:.4f} <= {entry_price * 0.5:.4f} (50% of entry)"

        # Time-based exit: exit if position open longer than max_position_hours
        entry_time = metadata['entry_time']
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=datetime.timezone.utc)
        hours_open = (datetime.datetime.now(datetime.timezone.utc) - entry_time).total_seconds() / 3600.0
        if hours_open > self.max_position_hours:
            return True, f"Time-based exit: {hours_open:.1f} hours > {self.max_position_hours:.1f} hours"

        # TODO: Evaluate invalidation conditions based on market data (e.g., underlying price thresholds)
        # For simplicity, we skip complex condition evaluation here.

        return False, ""

    def _manage_positions(self, positions):
        """Manage open positions: evaluate exit conditions and submit exit orders if needed."""
        for pos in positions:
            contract = getattr(pos, 'symbol', None)
            if not contract:
                continue
            metadata = self.position_metadata.get(contract)
            if metadata is None:
                # No metadata, maybe we opened position before metadata tracking started; skip for now
                continue

            should_exit, reason = self._evaluate_exit_conditions(contract, pos, metadata)
            if should_exit:
                self.log.info("Exit condition met for %s: %s", contract, reason)
                # Submit sell order to close long position
                qty = metadata['quantity']
                side = "sell"  # assuming we are long (bought) the option
                internal_id = f"agt-exit-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
                try:
                    order = self.client.submit_market_order(
                        symbol=contract,
                        qty=qty,
                        side=side,
                        internal_id=internal_id,
                    )
                    self.log.info(
                        "EXIT order submitted %s qty=%s status=%s alpaca_id=%s",
                        contract, qty, order.status, getattr(order, 'alpaca_id', None)
                    )
                    # Record exit order in DB (optional)
                    # We could also journal the exit, but for simplicity we just log.
                except Exception as e:
                    self.log.error("Failed to submit exit order for %s: %s", contract, e)
                # Remove metadata after exit order submitted (position will be closed asynchronously)
                self._remove_position_metadata(contract)

    def _check_shutdown_conditions(self, account) -> str | None:
        """Check if any automatic shutdown conditions are met.
        Returns reason string if shutdown should be triggered, else None.
        """
        # Reset daily starting equity if new day
        today = datetime.datetime.now(datetime.timezone.utc).date()
        if self._daily_starting_equity is None or self._daily_start_date != today:
            self._daily_starting_equity = account.equity
            self._daily_start_date = today
            self.log.info(
                "Reset daily starting equity to %.2f for %s",
                self._daily_starting_equity,
                today.isoformat(),
            )

        # Update peak equity
        if self._peak_equity is None or account.equity > self._peak_equity:
            self._peak_equity = account.equity

        # Compute daily loss and drawdown
        daily_loss = 0.0
        if self._daily_starting_equity is not None and self._daily_starting_equity > 0:
            daily_loss = (self._daily_starting_equity - account.equity) / self._daily_starting_equity

        drawdown = 0.0
        if self._peak_equity is not None and self._peak_equity > 0:
            drawdown = (self._peak_equity - account.equity) / self._peak_equity

        # Check thresholds
        if daily_loss > self.settings.max_daily_loss:
            return f"Daily loss {daily_loss:.2%} exceeds max {self.settings.max_daily_loss:.2%}"
        if drawdown > self.settings.max_drawdown:
            return f"Drawdown {drawdown:.2%} exceeds max {self.settings.max_drawdown:.2%}"

        # Consecutive failures checked elsewhere; we just return the reason if already set
        if self._shutdown_reason is not None:
            return self._shutdown_reason

        return None

    def _record_success(self):
        """Record a successful operation (reset failure counter)."""
        if self._consecutive_failures > 0:
            self.log.info(
                "Successful operation after %d consecutive failures",
                self._consecutive_failures,
            )
        self._consecutive_failures = 0

    def _record_failure(self, exc: Exception | None = None):
        """Record a failure, increment counter, and possibly trigger shutdown."""
        self._consecutive_failures += 1
        self.log.warning(
            "Consecutive failure %d/%d",
            self._consecutive_failures,
            self.settings.max_consecutive_failures,
        )
        if self._consecutive_failures >= self.settings.max_consecutive_failures:
            self._shutdown_reason = (
                f"Consecutive failures {self._consecutive_failures} >= max {self.settings.max_consecutive_failures}"
            )
            self.log.error("Shutdown triggered: %s", self._shutdown_reason)

    def run_once(self, *, submit: bool = True) -> CycleResult:
        # Fetch account and positions, catching any connection/market data failures
        try:
            account = self.client.get_account()
            positions = self.client.list_positions()
            self._record_success()
        except Exception as e:
            self._record_failure(e)
            # If we cannot get basic account info, we cannot continue meaningfully.
            # Still return a minimal result to avoid breaking the loop.
            self.log.error("Failed to fetch account/positions: %s", e)
            return CycleResult(account={}, signals=[], actions=[])

        self.log.info(
            "Account equity=%.2f buying_power=%.2f positions=%d trading_enabled=%s",
            account.equity,
            account.buying_power,
            len(positions),
            self.settings.trading_enabled,
        )

        # Check for automatic shutdown conditions (daily loss, drawdown, consecutive failures)
        shutdown_reason = self._check_shutdown_conditions(account)
        if shutdown_reason is not None:
            if not self._trading_halted:
                self._shutdown_reason = shutdown_reason
                self._trading_halted = True
                self.log.warning("Trading halted due to: %s", shutdown_reason)
                # Persist shutdown status
                self.db.set_system_status('trading_halted', True)
                self.db.set_system_status('shutdown_reason', shutdown_reason)
            # Update status even if already halted (in case reason changed?)
            self.db.set_system_status('shutdown_reason', shutdown_reason)
        else:
            # No shutdown condition; ensure we are not halted
            if self._trading_halted:
                self._trading_halted = False
                self._shutdown_reason = None
                self.log.info("Trading resumed - shutdown conditions cleared")
                # Persist that trading is not halted
                self.db.set_system_status('trading_halted', False)
                self.db.set_system_status('shutdown_reason', "")
            else:
                # Ensure we have cleared any previous status
                self.db.set_system_status('trading_halted', False)
                self.db.set_system_status('shutdown_reason', "")

        # Manage existing positions (exits) - always run, regardless of trading halted
        self._manage_positions(positions)

        # Prepare market state for AI evaluation
        market_state = {
            "underlyings": self.settings.underlying_list,
            "account": account.model_dump(),
            "positions": [p.model_dump(mode="json") for p in positions],
        }

        # Calculate market regime for dashboard
        spy_bars = self.market.bars("SPY", days=50) if "SPY" in self.settings.underlying_list else self.market.bars("SPY", days=50)
        if spy_bars and len(spy_bars) >= 30:
            spy_price = last_close(spy_bars)
            spy_ma_200 = sma(spy_bars, 200)
            spy_mom_50 = momentum(spy_bars, 50) if len(spy_bars) >= 51 else None
            spy_atr = atr(spy_bars, 20)

            regime = "RANGE_BOUND"  # Default
            regime_confidence = 0.0

            if spy_ma_200 and spy_mom_50 is not None and spy_price:
                if spy_price > spy_ma_200 and spy_mom_50 > 0.05:
                    regime = "BULL_TREND"
                    regime_confidence = min(90.0, 60.0 + (spy_mom_50 * 100))
                elif spy_price < spy_ma_200 and spy_mom_50 < -0.05:
                    regime = "BEAR_TREND"
                    regime_confidence = min(90.0, 60.0 + (abs(spy_mom_50) * 100))
                else:
                    regime = "RANGE_BOUND"
                    regime_confidence = 70.0

            # Check for high volatility
            if spy_atr and spy_price:
                spy_atr_percent = (spy_atr / spy_price) * 100
                if spy_atr_percent > 5.0:
                    regime = "HIGH_VOLATILITY"
                    regime_confidence = min(85.0, 50.0 + (spy_atr_percent - 5.0) * 5.0)

            self._market_regime = regime
            self._regime_confidence = regime_confidence

            # Store regime in system status for dashboard
            self.db.set_system_status('market_regime', {
                'regime': regime,
                'confidence': regime_confidence
            })

        self.log.info("About to generate signals")
        signals = self.strategy.generate_signals(market_state)
        self.log.info("Generated %d signal(s)", len(signals))

        # Store signals for dashboard
        self._latest_signals = signals
        self._candidates_count = len(signals)

        actions: list[dict[str, Any]] = []
        qualified_signals = 0
        for signal in signals:
            duplicate = bool(signal.contract and self.db.has_open_order(signal.contract))

            # AI Supervisor Evaluation (Phase 6) - only if enabled
            ai_decision = None
            if self.ai_supervisor is not None:
                # Get current price for underlying
                quote = self.market.quote(signal.underlying)
                current_price = quote.mid or quote.last or 0.0

                # Extract features for the underlying
                bars = self.market.bars(signal.underlying, days=30)
                features = {}
                if bars:
                    from backend.app.features.engine import (
                        returns, realized_volatility, sma, ema,
                        momentum, volume_change, atr, rsi, last_close
                    )

                    # Calculate various features
                    if len(bars) >= 2:
                        rets = returns(bars)
                        if rets and len(rets) > 0:
                            features['return_1d'] = rets[-1]

                    features['realized_volatility_20'] = realized_volatility(bars, 20) or 0.0
                    features['sma_20'] = sma(bars, 20) or 0.0
                    features['ema_20'] = ema(bars, 20) or 0.0
                    features['momentum_5'] = momentum(bars, 5) or 0.0
                    features['volume_change_20'] = volume_change(bars, 20) or 0.0
                    features['atr_14'] = atr(bars, 14) or 0.0
                    features['rsi_14'] = rsi(bars, 14) or 50.0
                    features['last_close'] = last_close(bars) or 0.0

                    # Price relative to moving averages
                    if features['sma_20'] > 0:
                        features['price_to_sma20'] = current_price / features['sma_20'] - 1.0
                    if features['ema_20'] > 0:
                        features['price_to_ema20'] = current_price / features['ema_20'] - 1.0

                # Get options data for the signal's contract
                options_snapshot = None
                if signal.contract:
                    options_snapshot = self.market.option_snapshot(signal.contract, underlying_price=current_price)

                # Prepare input for AI supervisor
                ai_input = AIInput(
                    underlying=signal.underlying,
                    price=current_price,
                    features=features,
                    signals=[signal],
                    options=[options_snapshot] if options_snapshot else [],
                    portfolio={"account": account.model_dump()},
                    risk={
                        "max_risk_per_trade": self.settings.max_risk_per_trade,
                        "max_portfolio_exposure": self.settings.max_portfolio_exposure,
                    }
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
                        ai_decision=json.dumps(ai_output.__dict__),
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
            # Determine if we should submit new orders: only if trading not halted and submit flag is True
            effective_submit = submit and (not self._trading_halted) and self.settings.trading_enabled
            if decision.approved:
                qualified_signals += 1
            if decision.approved and effective_submit:
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
                # Store metadata for new position
                if position:
                    self._update_position_metadata(effective_signal.contract, order, position, effective_signal, ai_decision)
            else:
                if not self.settings.trading_enabled:
                    self.log.info(
                        "TRADE REJECTED %s reasons=%s (trading disabled via kill switch)",
                        effective_signal.contract,
                        "; ".join(decision.reasons),
                    )
                elif self._trading_halted:
                    self.log.info(
                        "TRADE REJECTED %s reasons=%s (trading halted due to shutdown condition)",
                        effective_signal.contract,
                        "; ".join(decision.reasons),
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
                ai_decision=json.dumps(ai_decision.__dict__) if ai_decision is not None else json.dumps(AIOutput(
                    decision="HOLD", confidence=0.0, contract=None,
                    thesis="AI supervisor disabled", expected_horizon="N/A",
                    risk_factors=[], invalidation_conditions=[]
                ).__dict__),
                risk_decision=decision,
                execution=record.get("order"),
                result=record.get("position") or {"rejected": not decision.approved, "reasons": decision.reasons},
            )
            actions.append(record)
            if decision.approved and effective_submit:
                # Refresh positions after order submission
                positions = self.client.list_positions()

        # Store qualified count for dashboard
        self._qualified_count = qualified_signals

        # Store signal metadata in system status for dashboard
        self.db.set_system_status('signal_metadata', {
            'candidates_count': self._candidates_count,
            'qualified_count': self._qualified_count,
            'latest_signals': [
                {
                    'underlying': s.underlying,
                    'direction': s.direction,
                    'confidence': s.confidence,
                    'contract': s.contract,
                    'thesis': s.thesis[:200] if s.thesis else ""  # Limit length
                }
                for s in signals[:10]  # Store top 10 signals
            ]
        })

        if not signals:
            self.db.journal(
                result={"note": "no signals this cycle"},
                risk_decision={"approved": False, "reasons": ["no quantitative opportunity"]},
            )

        return CycleResult(account=account.model_dump(), signals=signals, actions=actions)


def build_live_loop() -> TradingLoop:
    settings = get_settings()
    return TradingLoop(LiveAlpacaClient(settings), settings)