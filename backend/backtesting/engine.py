"""
Backtesting engine for trading strategies.

This engine simulates the trading process over historical data,
allowing strategies to be evaluated without risking real capital.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import json

from backend.app.config.settings import Settings
from backend.app.data.models import (
    Signal,
    OptionSnapshot,
    OrderRecord,
    PositionSnapshot,
    AccountSnapshot,
    RiskDecision
)
from backend.app.features.engine import (
    returns,
    momentum,
    realized_volatility,
    sma,
    ema,
    rsi,
    atr,
    volume_change,
    last_close
)
from backend.app.strategies.base import Strategy
from backend.app.risk.engine import RiskEngine
from backend.app.execution.engine import ExecutionEngine
from backend.app.data.client import AlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.app.database.db import Database
from .data import HistoricalDataManager, HistoricalBar
from .synthetic_options import BlackScholesModel, SyntheticOptionChain, create_synthetic_option_data


@dataclass
class BacktestTrade:
    """Represents a completed trade in the backtest."""
    entry_time: datetime
    exit_time: datetime
    underlying: str
    contract_symbol: str
    direction: str  # "long" or "short"
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    holding_period_days: int
    entry_signal: Optional[Signal] = None
    exit_reason: str = ""  # "signal_reversal", "stop_loss", "take_profit", "expiration", "manual"


@dataclass
class BacktestPosition:
    """Represents an open position during backtesting."""
    contract_symbol: str
    underlying: str
    direction: str
    quantity: float
    entry_price: float
    entry_time: datetime
    entry_signal: Optional[Signal] = None
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0


@dataclass
class BacktestResults:
    """Results from a backtest run."""
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_trade: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0

    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    average_holding_period: float = 0.0

    # Capital curve
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)

    # Individual trades
    trades: List[BacktestTrade] = field(default_factory=list)

    # Final state
    final_equity: float = 0.0
    initial_equity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization."""
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "average_trade": self.average_trade,
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "average_holding_period": self.average_holding_period,
            "final_equity": self.final_equity,
            "initial_equity": self.initial_equity,
            "trades": [
                {
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                    "underlying": t.underlying,
                    "contract_symbol": t.contract_symbol,
                    "direction": t.direction,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "quantity": t.quantity,
                    "pnl": t.pnl,
                    "pnl_percent": t.pnl_percent,
                    "holding_period_days": t.holding_period_days,
                    "exit_reason": t.exit_reason
                }
                for t in self.trades
            ],
            "equity_curve": [
                {
                    "timestamp": ts.isoformat(),
                    "equity": eq
                }
                for ts, eq in self.equity_curve
            ]
        }


class BacktestEngine:
    """
    Main backtesting engine that orchestrates the backtest process.

    The engine simulates:
    1. Historical data feeding
    2. Signal generation from strategies
    3. Risk management decisions
    4. Order execution simulation
    5. Position tracking and P&L calculation
    6. Performance metrics calculation
    """

    def __init__(
        self,
        settings: Settings,
        historical_data_manager: Optional[HistoricalDataManager] = None
    ):
        self.settings = settings
        self.historical_data_manager = historical_data_manager or HistoricalDataManager()

        # Initialize components (using mocks for historical data)
        self.risk_engine = RiskEngine(settings)
        # For backtesting, we'll use a mock Alpaca client that doesn't make real API calls
        self.alpaca_client = self._create_mock_alpaca_client()
        self.market_data = MarketDataService(self.alpaca_client)
        self.execution_engine = ExecutionEngine(self.alpaca_client, Database(":memory:"))
        self.db = Database(":memory:")  # In-memory database for backtesting

        # Black-Scholes model for synthetic options
        self.options_model = BlackScholesModel(
            risk_free_rate=0.05,  # 5% risk-free rate
            dividend_yield=0.0
        )

        # State tracking
        self.current_date: Optional[date] = None
        self.current_time: Optional[datetime] = None
        self.positions: Dict[str, BacktestPosition] = {}
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.daily_returns: List[float] = []

    def _create_mock_alpaca_client(self) -> AlpacaClient:
        """
        Create a mock Alpaca client for backtesting.

        In a real implementation, this would be a subclass that overrides
        the API methods to work with historical/synthetic data instead
        of making real API calls.
        """
        # Use the existing MockAlpacaClient for backtesting
        from backend.app.data.mock_alpaca import MockAlpacaClient
        return MockAlpacaClient()

    def run_backtest(
        self,
        strategy: Strategy,
        symbols: List[str],
        start_date: date,
        end_date: date,
        initial_capital: float = 100000.0,
        frequency: str = "1Day"  # How often to generate signals
    ) -> BacktestResults:
        """
        Run a backtest for a strategy over historical data.

        Args:
            strategy: The strategy to test
            symbols: List of underlying symbols to trade
            start_date: Start date for backtest (inclusive)
            end_date: End date for backtest (inclusive)
            initial_capital: Starting capital
            frequency: How often to evaluate signals ("1Day", "1Hour", etc.)

        Returns:
            BacktestResults object with performance metrics
        """
        # Reset state
        self._reset_state(initial_capital)

        # Set the backtest date range
        self.current_date = start_date

        # Convert frequency to timedelta
        if frequency == "1Day":
            delta = timedelta(days=1)
        elif frequency == "1Hour":
            delta = timedelta(hours=1)
        else:
            # Default to daily
            delta = timedelta(days=1)

        # Main backtest loop
        current_time = datetime.combine(start_date, datetime.min.time())
        end_time = datetime.combine(end_date, datetime.min.time())

        while current_time <= end_time:
            # Update current date/time
            self.current_date = current_time.date()
            self.current_time = current_time

            # Fetch historical data up to current point
            # For each symbol, get historical data
            symbol_data: Dict[str, List[HistoricalBar]] = {}
            for symbol in symbols:
                # Get data from start_date to current_date
                hist_bars = self.historical_data_manager.get_historical_bars(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=self.current_date,
                    timeframe="1Day"  # We'll use daily data for simplicity
                )
                if hist_bars:
                    symbol_data[symbol] = hist_bars

            # If we have no data, skip to next period
            if not symbol_data:
                current_time += delta
                continue

            # Generate market state for the strategy
            market_state = self._create_market_state(symbol_data)

            # Generate signals from the strategy
            try:
                signals = strategy.generate_signals(market_state)
            except Exception as e:
                print(f"Error generating signals for {strategy.name} at {current_time}: {e}")
                signals = []

            # Process signals (similar to live trading pipeline)
            self._process_signals(signals, current_time)

            # Update positions with current market prices
            self._update_positions(symbol_data, current_time)

            # Record equity curve point
            current_equity = self._calculate_current_equity(symbol_data)
            self.equity_curve.append((current_time, current_equity))

            # Calculate daily return (if we have previous day's equity)
            if len(self.equity_curve) > 1:
                prev_equity = self.equity_curve[-2][1]
                if prev_equity > 0:
                    daily_return = (current_equity - prev_equity) / prev_equity
                    self.daily_returns.append(daily_return)

            # Move to next time period
            current_time += delta

        # Close any remaining positions at the end of the backtest
        self._close_all_positions(end_time, symbol_data)

        # Calculate and return results
        return self._calculate_results()

    def _reset_state(self, initial_capital: float):
        """Reset the backtest engine state."""
        self.positions.clear()
        self.trades.clear()
        self.equity_curve.clear()
        self.daily_returns.clear()

        # Start with initial capital
        self.equity_curve.append((datetime.min, initial_capital))

    def _create_market_state(self, symbol_data: Dict[str, List[HistoricalBar]]) -> Dict[str, Any]:
        """
        Create market state dictionary for strategy consumption.

        Converts our internal HistoricalBar format to the format
        expected by strategies (which use backend.app.data.models.Bar).
        """
        market_state = {
            "underlyings": list(symbol_data.keys()),
            "bars_data": {}
        }

        for symbol, hist_bars in symbol_data.items():
            # Convert HistoricalBar to backend Bar objects
            backend_bars = [bar.to_backend_bar() for bar in hist_bars]
            market_state["bars_data"][symbol] = backend_bars

        return market_state

    def _process_signals(self, signals: List[Signal], current_time: datetime):
        """
        Process trading signals (similar to pipeline.py logic).

        This mimics the live trading pipeline: signal -> risk check -> execution.
        """
        # Get current account state
        account = self._get_current_account()

        # Get current positions
        positions = [self._position_to_backend(pos) for pos in self.positions.values()]

        for signal in signals:
            # Skip if signal has no contract (can't trade)
            if not signal.contract:
                continue

            # Check for duplicate orders (simplified)
            duplicate = self._has_open_order(signal.contract)

            # Evaluate risk
            decision = self.risk_engine.evaluate(
                signal,
                account,
                positions,
                trading_enabled=self.settings.trading_enabled,
                duplicate_open=duplicate
            )

            if decision.approved and decision.qty > 0:
                # Execute the trade
                self._execute_trade(signal, decision, current_time)
            # Note: In a more complete implementation, we'd also handle signal exits

    def _execute_trade(self, signal: Signal, decision: RiskDecision, current_time: datetime):
        """Execute a trade based on an approved signal."""
        # In live trading, this would call the execution engine
        # For backtesting, we'll create a position directly

        # Determine trade direction from signal
        direction = signal.direction  # "long" or "short"

        # Get the option price from the signal snapshot
        if not signal.snapshot or not signal.snapshot.quote:
            return

        entry_price = signal.snapshot.quote.mid
        if entry_price is None or entry_price <= 0:
            return

        quantity = decision.qty

        # Create the position
        position = BacktestPosition(
            contract_symbol=signal.contract,
            underlying=signal.underlying,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=current_time,
            entry_signal=signal
        )

        self.positions[signal.contract] = position

        # Record in equity curve (we'll update the last point)
        # The equity curve will be updated in the main loop

    def _update_positions(self, symbol_data: Dict[str, List[HistoricalBar]], current_time: datetime):
        """Update open positions with current market prices."""
        # Get current prices for all underlying symbols
        underlying_prices: Dict[str, float] = {}

        for symbol, bars in symbol_data.items():
            if bars:
                latest_bar = bars[-1]
                underlying_prices[symbol] = latest_bar.close

        # Update each position
        for contract_symbol, position in list(self.positions.items()):
            # Get underlying price for this position's underlying
            underlying_price = underlying_prices.get(position.underlying)
            if underlying_price is None:
                continue

            # For simplicity in backtracking, we'll estimate option price change
            # based on underlying price change and delta
            # A more sophisticated approach would re-price the option using Black-Scholes

            # Calculate unrealized P&L
            # This is a simplification - in reality we'd need the current option price
            # For now, we'll approximate based on underlying movement

            # Update MFE and MAE
            # (Maximum Favorable/Adverse Excursion)
            # This would require tracking the option price over time

            # Check if we should close the position based on signals or time
            # This would be handled by exit signals in a complete implementation

            pass  # Position updating logic would go here

    def _close_all_positions(self, current_time: datetime, symbol_data: Dict[str, List[HistoricalBar]]):
        """Close all open positions at the end of the backtest."""
        underlying_prices: Dict[str, float] = {}
        for symbol, bars in symbol_data.items():
            if bars:
                latest_bar = bars[-1]
                underlying_prices[symbol] = latest_bar.close

        for contract_symbol, position in list(self.positions.items()):
            self._close_position(
                position,
                current_time,
                underlying_prices.get(position.underlying, 0.0),
                "end_of_backtest"
            )

    def _close_position(
        self,
        position: BacktestPosition,
        exit_time: datetime,
        exit_price: float,
        exit_reason: str
    ):
        """Close a position and record the trade."""
        if position.contract_symbol not in self.positions:
            return

        # Calculate P&L
        # This is a simplification - we're treating the option as if it trades 1:1 with underlying
        # In reality, options have non-linear payoff

        if position.direction == "long":
            pnl = (exit_price - position.entry_price) * position.quantity * 100  # Options multiplier
        else:  # short
            pnl = (position.entry_price - exit_price) * position.quantity * 100

        pnl_percent = pnl / (position.entry_price * position.quantity * 100) if position.entry_price > 0 else 0

        # Create trade record
        trade = BacktestTrade(
            entry_time=position.entry_time,
            exit_time=exit_time,
            underlying=position.underlying,
            contract_symbol=position.contract_symbol,
            direction=position.direction,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            pnl=pnl,
            pnl_percent=pnl_percent,
            holding_period_days=(exit_time - position.entry_time).days,
            entry_signal=position.entry_signal,
            exit_reason=exit_reason
        )

        self.trades.append(trade)

        # Remove position
        del self.positions[position.contract_symbol]

    def _has_open_order(self, contract_symbol: str) -> bool:
        """Check if there's an open order for a contract (simplified)."""
        # In live trading, this checks the database
        # For backtesting, we'll simplify
        return contract_symbol in self.positions

    def _get_current_account(self) -> AccountSnapshot:
        """Get current account state for risk checking."""
        # Calculate current equity
        current_equity = self._calculate_current_equity({})  # Would pass symbol_data in real implementation

        return AccountSnapshot(
            equity=current_equity,
            cash=current_equity,  # Simplified
            buying_power=current_equity * 4,  # 4x buying power (reg T)
            portfolio_value=current_equity,
            last_equity=current_equity,
            status="ACCOUNT_STATUS_ACTIVE",
            options_approved_level=3,
            trading_blocked=False
        )

    def _calculate_current_equity(self, symbol_data: Dict[str, List[HistoricalBar]]) -> float:
        """Calculate current account equity including open positions."""
        # Start with base equity (would come from settings or initial capital)
        base_equity = 100000.0  # This should come from initial capital

        # Add/subtract unrealized P&L from positions
        # This is simplified - in reality we'd calculate based on current option prices
        unrealized_pnl = 0.0

        for position in self.positions.values():
            # Simplified P&L calculation
            # In reality, we'd need current option prices
            underlying_price = 0.0
            if position.underlying in symbol_data and symbol_data[position.underlying]:
                latest_bar = symbol_data[position.underlying][-1]
                underlying_price = latest_bar.close

            if underlying_price > 0:
                if position.direction == "long":
                    unrealized_pnl += (underlying_price - position.entry_price) * position.quantity * 100
                else:
                    unrealized_pnl += (position.entry_price - underlying_price) * position.quantity * 100

        return base_equity + unrealized_pnl

    def _position_to_backend(self, position: BacktestPosition) -> PositionSnapshot:
        """Convert our BacktestPosition to backend PositionSnapshot for risk engine."""
        return PositionSnapshot(
            symbol=position.contract_symbol,
            qty=position.quantity,
            side=position.direction,
            avg_entry_price=position.entry_price,
            current_price=position.entry_price,  # Simplified
            market_value=position.quantity * position.entry_price * 100,
            unrealized_pl=0.0,  # Simplified
            asset_class="OPTION"
        )

    def _calculate_results(self) -> BacktestResults:
        """Calculate final performance metrics from the backtest."""
        if not self.trades:
            return BacktestResults(
                initial_equity=self.equity_curve[0][1] if self.equity_curve else 0.0,
                final_equity=self.equity_curve[-1][1] if self.equity_curve else 0.0
            )

        # Basic trade statistics
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]

        total_return = sum(t.pnl for t in self.trades)
        initial_equity = self.equity_curve[0][1] if self.equity_curve else 100000.0
        final_equity = self.equity_curve[-1][1] if self.equity_curve else initial_equity

        # Calculate returns
        if initial_equity > 0:
            total_return_percent = total_return / initial_equity
        else:
            total_return_percent = 0.0

        # Annualized return (simplified)
        if len(self.equity_curve) > 1:
            days = (self.equity_curve[-1][0] - self.equity_curve[0][0]).days
            if days > 0:
                annualized_return = (1 + total_return_percent) ** (365 / days) - 1
            else:
                annualized_return = 0.0
        else:
            annualized_return = 0.0

        # Sharpe ratio (simplified)
        if self.daily_returns and len(self.daily_returns) > 1:
            avg_return = np.mean(self.daily_returns)
            std_return = np.std(self.daily_returns)
            if std_return > 0:
                sharpe_ratio = (avg_return / std_return) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # Sortino ratio (simplified - using downside deviation)
        if self.daily_returns and len(self.daily_returns) > 1:
            downside_returns = [r for r in self.daily_returns if r < 0]
            if downside_returns:
                downside_std = np.std(downside_returns)
                if downside_std > 0:
                    sortino_ratio = (np.mean(self.daily_returns) / downside_std) * np.sqrt(252)
                else:
                    sortino_ratio = 0.0
            else:
                sortino_ratio = sharpe_ratio  # If no downside deviation, same as sharpe
        else:
            sortino_ratio = 0.0

        # Max drawdown
        max_drawdown = self._calculate_max_drawdown()

        # Win rate
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0.0

        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Average trade
        average_trade = np.mean([t.pnl for t in self.trades]) if self.trades else 0.0

        # Best/worst trade
        best_trade = max([t.pnl for t in self.trades]) if self.trades else 0.0
        worst_trade = min([t.pnl for t in self.trades]) if self.trades else 0.0

        # Average holding period
        average_holding_period = np.mean([t.holding_period_days for t in self.trades]) if self.trades else 0.0

        return BacktestResults(
            total_return=total_return_percent,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_trade=average_trade,
            best_trade=best_trade,
            worst_trade=worst_trade,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            average_holding_period=average_holding_period,
            equity_curve=self.equity_curve,
            trades=self.trades,
            final_equity=final_equity,
            initial_equity=initial_equity
        )

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0.0

        peak = self.equity_curve[0][1]
        max_dd = 0.0

        for _, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return max_dd


def run_strategy_backtest(
    strategy: Strategy,
    symbols: List[str],
    start_date: date,
    end_date: date,
    initial_capital: float = 100000.0
) -> BacktestResults:
    """
    Convenience function to run a backtest on a strategy.

    Args:
        strategy: The strategy to backtest
        symbols: List of symbols to trade
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_capital: Starting capital

    Returns:
        BacktestResults object
    """
    engine = BacktestEngine(settings=StrategySettings())  # Would need proper settings
    return engine.run_backtest(
        strategy=strategy,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )


# Placeholder for settings - in reality we'd import from backend.app.config.settings
class StrategySettings:
    """Placeholder settings class for backtesting."""
    def __init__(self):
        self.trading_enabled = True
        self.max_bid_ask_spread = 0.25
        self.min_open_interest = 0
        self.min_option_volume = 0
        self.min_dte = 0
        self.max_dte = 45
        self.max_risk_per_trade = 0.01
        self.max_portfolio_exposure = 0.2
        self.max_positions = 5
        self.max_underlying_concentration = 0.15