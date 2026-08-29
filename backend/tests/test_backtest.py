"""
Tests for the backtesting framework.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from backend.app.config.settings import Settings
from backend.app.data.models import Bar
from backend.backtesting.data import HistoricalDataManager, HistoricalBar
from backend.backtesting.synthetic_options import BlackScholesModel, SyntheticOptionChain
from backend.backtesting.engine import BacktestEngine
from strategies.research.volatility_mispricing import VolatilityMispricingStrategy


def test_historical_data_manager_import():
    """Test that we can import the historical data manager."""
    from backend.backtesting.data import HistoricalDataManager
    assert True


def test_historical_data_manager_initialization():
    """Test HistoricalDataManager initialization."""
    manager = HistoricalDataManager()
    assert manager is not None
    assert hasattr(manager, '_data_cache')
    assert isinstance(manager._data_cache, dict)


def test_synthetic_options_import():
    """Test that we can import synthetic options components."""
    from backend.backtesting.synthetic_options import BlackScholesModel, SyntheticOptionChain
    assert True


def test_black_scholes_model_initialization():
    """Test BlackScholesModel initialization."""
    model = BlackScholesModel()
    assert model is not None
    assert model.risk_free_rate == 0.05
    assert model.dividend_yield == 0.0

    # Test with custom parameters
    model2 = BlackScholesModel(risk_free_rate=0.03, dividend_yield=0.02)
    assert model2.risk_free_rate == 0.03
    assert model2.dividend_yield == 0.02


def test_synthetic_option_chain_initialization():
    """Test SyntheticOptionChain initialization."""
    model = BlackScholesModel()
    chain = SyntheticOptionChain(model)
    assert chain is not None
    assert chain.model is model


def test_backtest_engine_import():
    """Test that we can import the backtest engine."""
    from backend.backtesting.engine import BacktestEngine
    assert True


def test_backtest_engine_initialization():
    """Test BacktestEngine initialization."""
    # Create a minimal settings object
    settings = Settings(
        trading_enabled=True,
        max_bid_ask_spread=0.25,
        min_open_interest=0,
        min_option_volume=0,
        min_dte=0,
        max_dte=45,
        max_risk_per_trade=0.01,
        max_portfolio_exposure=0.2,
        max_positions=5,
        max_underlying_concentration=0.15
    )

    engine = BacktestEngine(settings=settings)
    assert engine is not None
    assert engine.settings is settings
    assert engine.historical_data_manager is not None
    assert engine.risk_engine is not None


def test_performance_metrics_import():
    """Test that we can import performance metrics."""
    from backend.backtesting.metrics import PerformanceMetrics
    assert True


def test_run_backtest_script_import():
    """Test that we can import the run_backtest script."""
    # This is just to make sure the script is syntactically correct
    import run_backtest
    assert True


def test_historical_bar_creation():
    """Test HistoricalBar creation and conversion."""
    from backend.app.data.models import Bar
    from datetime import datetime, timezone

    hist_bar = HistoricalBar(
        symbol="TEST",
        timestamp=datetime.now(timezone.utc),
        open=100.0,
        high=105.0,
        low=95.0,
        close=102.0,
        volume=1000.0
    )

    # Test conversion to backend Bar
    backend_bar = hist_bar.to_backend_bar()
    assert isinstance(backend_bar, Bar)
    assert backend_bar.symbol == "TEST"
    assert backend_bar.open == 100.0
    assert backend_bar.high == 105.0
    assert backend_bar.low == 95.0
    assert backend_bar.close == 102.0
    assert backend_bar.volume == 1000.0


def test_volatility_mispricing_strategy_with_backtest():
    """Test that VolatilityMispricingStrategy can work in backtest context."""
    settings = Settings(
        underlyings="SPY",
        max_bid_ask_spread=0.25,
        min_open_interest=0,
        min_option_volume=0,
        min_dte=0,
        max_dte=365,
        max_risk_per_trade=0.01,
        max_portfolio_exposure=0.2,
        max_positions=5,
        max_underlying_concentration=0.15,
        trading_enabled=True
    )

    # We can't fully test the strategy without market data, but we can test initialization
    strategy = VolatilityMispricingStrategy(None, settings)
    assert strategy is not None
    assert strategy.name == "volatility_mispricing"


if __name__ == "__main__":
    # This allows running the test file directly
    import pytest
    pytest.main([__file__, "-v"])