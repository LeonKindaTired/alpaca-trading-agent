"""
Backtesting module for the Alpaca AI Trading Agent.

This module provides tools for backtesting trading strategies using historical data.
When historical options data is not available, it uses synthetic options pricing
based on the Black-Scholes model.
"""

from .data import HistoricalDataManager
from .synthetic_options import BlackScholesModel, SyntheticOptionChain
from .engine import BacktestEngine
from .metrics import PerformanceMetrics

__all__ = [
    "HistoricalDataManager",
    "BlackScholesModel",
    "SyntheticOptionChain",
    "BacktestEngine",
    "PerformanceMetrics",
]