#!/usr/bin/env python3
"""Test different parameters for the Liquid Momentum strategy."""

from datetime import date, timedelta
from backend.app.config.settings import Settings
from backend.backtesting.engine import BacktestEngine
from backend.app.data.mock_alpaca import MockAlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy
import sys

def test_parameters(threshold, lookback, max_risk_per_trade=0.02, time_exit_hours=240):
    """Test a specific parameter combination."""
    try:
        # Setup
        client = MockAlpacaClient()
        market_data = MarketDataService(client)
        settings = Settings(
            underlyings='SPY,QQQ,IWM',
            max_bid_ask_spread=0.25,
            min_open_interest=0,
            min_option_volume=0,
            min_dte=0,
            max_dte=365,
            max_risk_per_trade=max_risk_per_trade,
            max_portfolio_exposure=0.3,
            max_positions=5,
            max_underlying_concentration=0.2,
            trading_enabled=True,
        )
        
        # Create custom strategy with given parameters
        class CustomLiquidMomentumStrategy(LiquidMomentumStrategy):
            def __init__(self, market, settings):
                super().__init__(market, settings)
                self.threshold = threshold
                
            def _signal_for(self, underlying):
                bars = self.market.bars(underlying, days=max(20, lookback+5))  # Ensure enough data
                from backend.app.features.engine import momentum, last_close
                mom = momentum(bars, lookback=lookback)
                close = last_close(bars)
                quote = self.market.quote(underlying)
                price = quote.mid or quote.last or close
                if mom is None or price is None:
                    return None
                if abs(mom) < self.threshold:
                    return None

                direction = "long" if mom > 0 else "short"
                right = "call" if direction == "long" else "put"
                chain = self.market.option_chain(
                    underlying,
                    min_dte=self.settings.min_dte,
                    max_dte=self.settings.max_dte,
                    right=right,
                    limit=100,
                )
                if not chain:
                    return None

                scored: list[tuple[float, object]] = []
                for contract in chain:
                    snap = self.market.option_snapshot(contract.symbol, underlying_price=price)
                    if snap.quote is None or snap.quote.mid is None:
                        continue
                    dist = abs(contract.strike - price) / price
                    spread = snap.quote.spread_pct
                    oi = contract.open_interest
                    if spread is None or oi is None:
                        continue
                    score = -(dist * 10.0 + spread * 5.0) + min(oi, 5000) / 5000.0
                    scored.append((score, snap))

                if not scored:
                    return None
                scored.sort(key=lambda x: x[0], reverse=True)
                best = scored[0][1]
                from backend.app.data.models import Signal
                from datetime import datetime, timezone
                return Signal(
                    underlying=underlying,
                    direction=direction,
                    confidence=min(0.85, 0.45 + abs(mom) * 20),
                    thesis=(
                        f"{underlying} {lookback}-day momentum {mom:.2%} -> {right} "
                        f"{best.contract.symbol} strike {best.contract.strike} exp {best.contract.expiration}"
                    ),
                    expected_edge=abs(mom),
                    contract=best.contract.symbol,
                    timestamp=datetime.now(timezone.utc),
                    snapshot=best,
                )
        
        strategy = CustomLiquidMomentumStrategy(market_data, settings)
        backtest_engine = BacktestEngine(settings=settings)
        
        # Run backtest for 90 days
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        
        # Temporarily modify the time-based exit in the engine
        original_engine_run = backtest_engine.run_backtest
        
        def custom_run_backtest(*args, **kwargs):
            # We'll modify the engine's time-based exit logic
            # For now, let's just run the standard backtest and see
            return original_engine_run(*args, **kwargs)
        
        result = backtest_engine.run_backtest(
            strategy=strategy,
            symbols=['SPY', 'QQQ', 'IWM'],
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000.0
        )
        
        return {
            'threshold': threshold,
            'lookback': lookback,
            'max_risk_per_trade': max_risk_per_trade,
            'time_exit_hours': time_exit_hours,
            'trades': result.total_trades,
            'return': result.total_return,
            'sharpe': result.sharpe_ratio,
            'sortino': result.sortino_ratio,
            'max_dd': result.max_drawdown,
            'win_rate': result.win_rate
        }
    except Exception as e:
        print(f"Error testing threshold={threshold}, lookback={lookback}: {e}")
        return None

# Test different momentum thresholds
print("Testing momentum thresholds...")
thresholds = [0.001, 0.002, 0.003, 0.005, 0.008, 0.010]
lookbacks = [3, 5, 10, 15]

results = []
for threshold in thresholds:
    for lookback in lookbacks:
        result = test_parameters(threshold, lookback)
        if result:
            results.append(result)
            print(f"Threshold {threshold:.3f}, Lookback {lookback}: {result['trades']:2d} trades, "
                  f"{result['return']:6.2%} return, {result['sharpe']:5.2f} Sharpe")

# Find best by Sharpe ratio
if results:
    best = max(results, key=lambda x: x['sharpe'] if x['sharpe'] > -999 else -999)
    print("\n" + "="*60)
    print("BEST PARAMETERS (by Sharpe ratio):")
    print(f"Threshold: {best['threshold']:.3f}")
    print(f"Lookback: {best['lookback']} days")
    print(f"Trades: {best['trades']}")
    print(f"Return: {best['return']:.2%}")
    print(f"Sharpe: {best['sharpe']:.2f}")
    print(f"Sortino: {best['sortino']:.2f}")
    print(f"Max DD: {best['max_dd']:.2%}")
    print(f"Win Rate: {best['win_rate']:.2%}")
