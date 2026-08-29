"""
Parameter optimization script for Liquid Momentum strategy.
Tests different parameter combinations and evaluates performance using backtesting.
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import itertools

# Add the backend directory to the path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.settings import Settings
from backend.app.data.mock_alpaca import MockAlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.backtesting.engine import BacktestEngine
import json


class OptimizableLiquidMomentumStrategy:
    """
    Liquid Momentum strategy with configurable parameters for optimization.
    """

    def __init__(self, market: MarketDataService, settings: Settings,
                 threshold: float = 0.004, lookback: int = 5,
                 analysis_days: int = 20, confidence_base: float = 0.45,
                 confidence_multiplier: float = 20.0,
                 dist_weight: float = 10.0, spread_weight: float = 5.0,
                 oi_cap: int = 5000):
        self.market = market
        self.settings = settings
        self.threshold = threshold
        self.lookback = lookback
        self.analysis_days = analysis_days
        self.confidence_base = confidence_base
        self.confidence_multiplier = confidence_multiplier
        self.dist_weight = dist_weight
        self.spread_weight = spread_weight
        self.oi_cap = oi_cap
        self.name = f"liquid_momentum_t{threshold}_lb{lookback}_ad{analysis_days}"

    def generate_signals(self, market_state: dict):
        from backend.app.data.models import Signal, OptionSnapshot
        from backend.app.features.engine import momentum, last_close

        symbols = market_state.get("underlyings") or self.settings.underlying_list
        signals = []

        for symbol in symbols:
            sig = self._signal_for(symbol)
            if sig:
                signals.append(sig)
        return signals

    def _signal_for(self, underlying: str):
        from backend.app.data.models import Signal, OptionSnapshot
        from backend.app.features.engine import momentum, last_close

        bars = self.market.bars(underlying, days=self.analysis_days)
        mom = momentum(bars, lookback=self.lookback)
        close = last_close(bars)
        quote = self.market.quote(underlying)
        price = quote.mid or quote.last or close

        if mom is None or price is None:
            return None

        if abs(mom) < self.threshold:
            return None

        direction = "long" if mom > 0 else "short"
        right = "call" if direction == "long" else "put"

        # Use settings for DTE constraints
        chain = self.market.option_chain(
            underlying,
            min_dte=self.settings.min_dte,
            max_dte=self.settings.max_dte,
            right=right,
            limit=100,
        )

        if not chain:
            return None

        scored = []
        for contract in chain:
            snap = self.market.option_snapshot(contract.symbol, underlying_price=price)
            if snap.quote is None or snap.quote.mid is None:
                continue

            dist = abs(contract.strike - price) / price
            spread = snap.quote.spread_pct
            oi = contract.open_interest

            if spread is None or oi is None:
                continue

            # Scoring formula: lower distance and spread is better, higher OI is better
            score = -(dist * self.dist_weight + spread * self.spread_weight) + min(oi, self.oi_cap) / self.oi_cap
            scored.append((score, snap))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]

        # Confidence calculation: base + momentum influence, capped
        confidence = min(0.85, self.confidence_base + abs(mom) * self.confidence_multiplier)

        return Signal(
            underlying=underlying,
            direction=direction,
            confidence=confidence,
            thesis=(
                f"{underlying} {self.lookback}-day momentum {mom:.2%} → {right} "
                f"{best.contract.symbol} strike {best.contract.strike} exp {best.contract.expiration}"
            ),
            expected_edge=abs(mom),
            contract=best.contract.symbol,
            timestamp=datetime.now(),
            snapshot=best,
        )


class HistoricalMockAlpacaClient(MockAlpacaClient):
    """
    Extended mock client that can return historical data for backtesting.
    """

    def __init__(self, initial_price: float = 450.0):
        super().__init__()
        self._spy_price = initial_price
        self._qqq_price = initial_price * 0.85  # QQQ typically lower than SPY
        self._iwm_price = initial_price * 0.5   # IWM typically lower than SPY
        self._price_history = {
            "SPY": [initial_price],
            "QQQ": [self._qqq_price],
            "IWM": [self._iwm_price]
        }
        self._day = 0
        self._volatility = 0.015  # 1.5% daily volatility

    def get_bars(self, symbol: str, *, days: int = 30) -> list:
        """
        Return historical bar data for backtesting.
        Generates realistic price movements with some trend and volatility.
        """
        from backend.app.data.models import Bar

        # Extend history if needed
        price_changes = []  # Store daily changes for volatility calculation
        while len(self._price_history[symbol]) < days:
            last_price = self._price_history[symbol][-1]

            # Add some mean reversion and trend
            if symbol == "SPY":
                trend = 0.0002  # Slight upward trend
            elif symbol == "QQQ":
                trend = 0.0003  # Slightly higher trend for tech
            else:  # IWM
                trend = 0.0001  # Slight trend for small caps

            mean_reversion = -0.05 * (self._price_history[symbol][-1] -
                                    sum(self._price_history[symbol][-10:])/min(len(self._price_history[symbol]), 10)) if len(self._price_history[symbol]) >= 10 else 0

            # Random walk with volatility
            change = trend + mean_reversion + (self._volatility * (0.5 - (hash(f"{last_price}{len(self._price_history[symbol])}") % 1000) / 500.0))
            price_changes.append(change)  # Store the change for this day
            new_price = last_price * (1 + change)
            self._price_history[symbol].append(new_price)

        # Return the last 'days' worth of price data as bars
        start_idx = max(0, len(self._price_history[symbol]) - days)
        price_slice = self._price_history[symbol][start_idx:]
        changes_slice = price_changes[start_idx:] if price_changes else [0.0] * len(price_slice)

        bars = []
        base_time = datetime.now() - timedelta(days=len(price_slice))

        for i, (price, change) in enumerate(zip(price_slice, changes_slice)):
            # Add some intraday volatility
            intraday_vol = abs(change) * 2 + 0.003 if i > 0 else 0.01

            high = price * (1 + abs(intraday_vol * 0.5))
            low = price * (1 - abs(intraday_vol * 0.5))
            open_price = price_slice[i-1] * (1 + intraday_vol * 0.3) if i > 0 else price

            # Ensure OHLC relationships
            high = max(high, open_price, price)
            low = min(low, open_price, price)

            bar = Bar(
                symbol=symbol,
                timestamp=base_time + timedelta(days=i),
                open=open_price,
                high=high,
                low=low,
                close=price,
                volume=50_000_000 + (i * 100000)  # Increasing volume trend
            )
            bars.append(bar)

        return bars


def create_historical_market_data_service() -> MarketDataService:
    """
    Create a market data service with historical data capability.
    """
    client = HistoricalMockAlpacaClient(initial_price=450.0)
    return MarketDataService(client)


def run_parameter_backtest(params_dict: dict, start_date: date, end_date: date) -> dict:
    """
    Run a backtest with specific parameter settings.
    """
    print(f"Testing params: {params_dict}")

    # Create settings
    settings = Settings(
        underlyings="SPY,QQQ,IWM",
        max_bid_ask_spread=0.25,
        min_open_interest=0,
        min_option_volume=0,
        min_dte=0,
        max_dte=365,
        max_risk_per_trade=0.02,
        max_portfolio_exposure=0.3,
        max_positions=5,
        max_underlying_concentration=0.2,
        trading_enabled=True,
    )

    # Create market data service
    market_data = create_historical_market_data_service()

    # Create strategy with parameters
    strategy = OptimizableLiquidMomentumStrategy(
        market=market_data,
        settings=settings,
        **params_dict
    )

    # Initialize backtest engine
    backtest_engine = BacktestEngine(settings=settings)

    try:
        # Run the backtest
        backtest_result = backtest_engine.run_backtest(
            strategy=strategy,
            symbols=["SPY", "QQQ", "IWM"],
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000.0
        )

        result = {
            "params": params_dict.copy(),
            "total_return": backtest_result.total_return,
            "annualized_return": backtest_result.annualized_return,
            "sharpe_ratio": backtest_result.sharpe_ratio,
            "sortino_ratio": backtest_result.sortino_ratio,
            "max_drawdown": backtest_result.max_drawdown,
            "win_rate": backtest_result.win_rate,
            "profit_factor": backtest_result.profit_factor,
            "total_trades": backtest_result.total_trades,
            "final_equity": backtest_result.final_equity
        }

        print(f"  Result: {backtest_result.total_return:.2%} return, "
              f"{backtest_result.sharpe_ratio:.2f} Sharpe, {backtest_result.max_drawdown:.2%} max DD, "
              f"{backtest_result.total_trades} trades")

        return result

    except Exception as e:
        print(f"  Error: {e}")
        return {
            "params": params_dict.copy(),
            "total_return": 0.0,
            "annualized_return": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "final_equity": 100000.0,
            "error": str(e)
        }


def main():
    """Run parameter optimization for Liquid Momentum strategy."""
    print("=== Liquid Momentum Strategy Parameter Optimization ===\n")

    # Define backtest period (30 days for quick testing)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    print(f"Backtest Period: {start_date} to {end_date}")
    print(f"Total Days: {(end_date - start_date).days}\n")

    # Base parameters (current strategy values)
    base_params = {
        "threshold": 0.004,
        "lookback": 5,
        "analysis_days": 20,
        "confidence_base": 0.45,
        "confidence_multiplier": 20.0,
        "dist_weight": 10.0,
        "spread_weight": 5.0,
        "oi_cap": 5000
    }

    # Define parameter ranges to test
    param_ranges = {
        "threshold": [0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.010],  # 0.2% to 1.0%
        "lookback": [3, 5, 7, 10, 15],  # 3-day to 15-day momentum
        "analysis_days": [10, 15, 20, 25, 30],  # 10 to 30 days of data
        "confidence_base": [0.3, 0.4, 0.45, 0.5, 0.6],
        "confidence_multiplier": [10.0, 15.0, 20.0, 25.0, 30.0],
        "dist_weight": [5.0, 8.0, 10.0, 12.0, 15.0],
        "spread_weight": [3.0, 5.0, 7.0, 10.0],
        "oi_cap": [1000, 2500, 5000, 7500, 10000]
    }

    # For a reasonable number of combinations, let's test one parameter at a time
    # keeping others at base values
    results = []

    print("Testing individual parameter variations...\n")

    for param_name, param_values in param_ranges.items():
        print(f"--- Testing {param_name} ---")

        for value in param_values:
            test_params = base_params.copy()
            test_params[param_name] = value

            result = run_parameter_backtest(test_params, start_date, end_date)
            results.append(result)
            print()

    # Also test some promising combinations
    print("--- Testing promising combinations ---")

    # Combination 1: Lower threshold, longer lookback
    combo1 = base_params.copy()
    combo1.update({
        "threshold": 0.003,
        "lookback": 7,
        "confidence_multiplier": 25.0
    })
    result1 = run_parameter_backtest(combo1, start_date, end_date)
    results.append(result1)

    # Combination 2: Higher threshold, shorter lookback (more aggressive)
    combo2 = base_params.copy()
    combo2.update({
        "threshold": 0.006,
        "lookback": 3,
        "confidence_multiplier": 15.0
    })
    result2 = run_parameter_backtest(combo2, start_date, end_date)
    results.append(result2)

    # Combination 3: Focus on liquidity (higher OI weight)
    combo3 = base_params.copy()
    combo3.update({
        "dist_weight": 8.0,
        "spread_weight": 3.0,
        "oi_cap": 10000
    })
    result3 = run_parameter_backtest(combo3, start_date, end_date)
    results.append(result3)

    # Sort results by Sharpe ratio (risk-adjusted return)
    valid_results = [r for r in results if r['sharpe_ratio'] > 0]
    valid_results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)

    # Display top results
    print("\n" + "="*80)
    print("TOP 10 PARAMETER COMBINATIONS (by Sharpe Ratio)")
    print("="*80)

    for i, result in enumerate(valid_results[:10]):
        params = result['params']
        print(f"{i+1:2d}. Return: {result['total_return']:>6.2%} | "
              f"Sharpe: {result['sharpe_ratio']:>5.2f} | "
              f"Max DD: {result['max_drawdown']:>5.2%} | "
              f"Trades: {result['total_trades']:>3d} | "
              f"Params: threshold={params['threshold']:.3f}, "
              f"lb={params['lookback']}, ad={params['analysis_days']}")

    # Show best overall
    if valid_results:
        best = valid_results[0]
        print("\n" + "="*80)
        print("BEST PARAMETER COMBINATION")
        print("="*80)
        print(f"Parameters: {best['params']}")
        print(f"Total Return: {best['total_return']:.2%}")
        print(f"Annualized Return: {best['annualized_return']:.2%}")
        print(f"Sharpe Ratio: {best['sharpe_ratio']:.2f}")
        print(f"Sortino Ratio: {best['sortino_ratio']:.2f}")
        print(f"Max Drawdown: {best['max_drawdown']:.2%}")
        print(f"Win Rate: {best['win_rate']:.2%}")
        print(f"Profit Factor: {best['profit_factor']:.2f}")
        print(f"Total Trades: {best['total_trades']}")
        print(f"Final Equity: ${best['final_equity']:,.2f}")

        # Compare to base parameters
        base_result = run_parameter_backtest(base_params, start_date, end_date)
        improvement = {
            "return": best['total_return'] - base_result['total_return'],
            "sharpe": best['sharpe_ratio'] - base_result['sharpe_ratio'],
            "max_dd": base_result['max_drawdown'] - best['max_drawdown'],  # Positive = improvement
            "trades": best['total_trades'] - base_result['total_trades']
        }

        print("\n" + "-"*80)
        print("IMPROVEMENT OVER BASE PARAMETERS")
        print("-"*80)
        print(f"Return: {improvement['return']:+.2%}")
        print(f"Sharpe Ratio: {improvement['sharpe']:+.2f}")
        print(f"Max Drawdown: {improvement['max_dd']:+.2%} (lower is better)")
        print(f"Trade Count: {improvement['trades']:+d}")

        # Save best parameters to file
        best_params_file = ROOT / "best_strategy_params.json"
        with open(best_params_file, 'w') as f:
            json.dump({
                "best_parameters": best['params'],
                "performance": {
                    "total_return": best['total_return'],
                    "annualized_return": best['annualized_return'],
                    "sharpe_ratio": best['sharpe_ratio'],
                    "sortino_ratio": best['sortino_ratio'],
                    "max_drawdown": best['max_drawdown'],
                    "win_rate": best['win_rate'],
                    "profit_factor": best['profit_factor'],
                    "total_trades": best['total_trades'],
                    "final_equity": best['final_equity']
                },
                "improvement_over_base": improvement,
                "test_period": f"{start_date} to {end_date}"
            }, f, indent=2)

        print(f"\nBest parameters saved to: {best_params_file}")

    print("\n" + "="*80)
    print("PARAMETER OPTIMIZATION COMPLETE")
    print("="*80)

    return len(valid_results) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)