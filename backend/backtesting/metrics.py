"""
Performance metrics calculation for backtesting results.
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple
from datetime import datetime

from .engine import BacktestResults


class PerformanceMetrics:
    """Calculates various performance metrics from backtest results."""

    @staticmethod
    def calculate_all(results: BacktestResults) -> dict:
        """
        Calculate all available performance metrics.

        Args:
            results: BacktestResults object

        Returns:
            Dictionary of metric names and values
        """
        metrics = {}

        # Basic return metrics
        metrics["total_return"] = results.total_return
        metrics["annualized_return"] = results.annualized_return

        # Risk-adjusted metrics
        metrics["sharpe_ratio"] = results.sharpe_ratio
        metrics["sortino_ratio"] = results.sortino_ratio
        metrics["max_drawdown"] = results.max_drawdown

        # Trading statistics
        metrics["win_rate"] = results.win_rate
        metrics["profit_factor"] = results.profit_factor
        metrics["average_trade"] = results.average_trade
        metrics["best_trade"] = results.best_trade
        metrics["worst_trade"] = results.worst_trade

        # Trade frequency and duration
        metrics["total_trades"] = results.total_trades
        metrics["average_holding_period"] = results.average_holding_period

        # Return distribution metrics
        if results.trades:
            returns = [t.pnl_percent for t in results.trades]
            metrics["return_std"] = np.std(returns) if len(returns) > 1 else 0.0
            metrics["return_skew"] = 0.0  # Would calculate skew
            metrics["return_kurtosis"] = 0.0  # Would calculate kurtosis

            # Percentiles
            metrics["return_5th_percentile"] = np.percentile(returns, 5) if returns else 0.0
            metrics["return_25th_percentile"] = np.percentile(returns, 25) if returns else 0.0
            metrics["return_50th_percentile"] = np.percentile(returns, 50) if returns else 0.0
            metrics["return_75th_percentile"] = np.percentile(returns, 75) if returns else 0.0
            metrics["return_95th_percentile"] = np.percentile(returns, 95) if returns else 0.0

        # Capital efficiency
        if results.initial_equity > 0:
            metrics["calmar_ratio"] = results.annualized_return / results.max_drawdown if results.max_drawdown > 0 else 0.0
        else:
            metrics["calmar_ratio"] = 0.0

        return metrics

    @staticmethod
    def print_report(results: BacktestResults):
        """Print a formatted performance report."""
        metrics = PerformanceMetrics.calculate_all(results)

        print("=" * 60)
        print("BACKTEST PERFORMANCE REPORT")
        print("=" * 60)
        print(f"Initial Equity:     ${results.initial_equity:,.2f}")
        print(f"Final Equity:       ${results.final_equity:,.2f}")
        print(f"Total Return:       {results.total_return:.2%}")
        print(f"Annualized Return:  {results.annualized_return:.2%}")
        print("-" * 60)
        print(f"Sharpe Ratio:       {results.sharpe_ratio:.2f}")
        print(f"Sortino Ratio:      {results.sortino_ratio:.2f}")
        print(f"Max Drawdown:       {results.max_drawdown:.2%}")
        print(f"Calmar Ratio:       {metrics.get('calmar_ratio', 0.0):.2f}")
        print("-" * 60)
        print(f"Total Trades:       {results.total_trades}")
        print(f"Winning Trades:     {results.winning_trades}")
        print(f"Losing Trades:      {results.losing_trades}")
        print(f"Win Rate:           {results.win_rate:.2%}")
        print(f"Profit Factor:      {results.profit_factor:.2f}")
        print("-" * 60)
        print(f"Average Trade:      ${results.average_trade:,.2f}")
        print(f"Best Trade:         ${results.best_trade:,.2f}")
        print(f"Worst Trade:        ${results.worst_trade:,.2f}")
        print(f"Average Holding Period: {results.average_holding_period:.1f} days")
        print("=" * 60)


def compare_strategies(results_list: List[Tuple[str, BacktestResults]]) -> dict:
    """
    Compare multiple strategy backtest results.

    Args:
        results_list: List of (strategy_name, BacktestResults) tuples

    Returns:
        Dictionary with comparison metrics
    """
    comparison = {}

    for name, results in results_list:
        metrics = PerformanceMetrics.calculate_all(results)
        comparison[name] = metrics

    return comparison


def print_strategy_comparison(results_list: List[Tuple[str, BacktestResults]]):
    """Print a formatted comparison of multiple strategies."""
    if not results_list:
        print("No strategies to compare")
        return

    print("=" * 80)
    print("STRATEGY COMPARISON")
    print("=" * 80)

    # Header
    print(f"{'Strategy':<20} {'Return':<10} {'Sharpe':<8} {'Sortino':<8} {'Max DD':<10} {'Win Rate':<10} {'Trades':<8}")
    print("-" * 80)

    # Data rows
    for name, results in results_list:
        print(f"{name:<20} {results.total_return:>9.2%} {results.sharpe_ratio:>7.2f} {results.sortino_ratio:>7.2f} "
              f"{results.max_drawdown:>9.2%} {results.win_rate:>9.2%} {results.total_trades:>7d}")

    print("=" * 80)