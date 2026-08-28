"""
Tests for the strategies.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from backend.app.config.settings import Settings
from backend.app.data.mock_alpaca import MockAlpacaClient
from backend.app.data.models import (
    Greeks,
    OptionContract,
    OptionRight,
    OptionSnapshot,
    Quote,
    Bar,
)
from strategies.research.mean_reversion import MeanReversionStrategy
from strategies.research.volatility_mispricing import VolatilityMispricingStrategy
from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy
from backend.app.data.market_data import MarketDataService


def test_strategy_imports():
    """Test that we can import the strategies."""
    from strategies.research.mean_reversion import MeanReversionStrategy
    from strategies.research.volatility_mispricing import VolatilityMispricingStrategy
    from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy
    assert True  # If we get here, imports worked


def test_liquid_momentum_strategy_init():
    """Test LiquidMomentumStrategy initialization."""
    client = MockAlpacaClient()
    market = MarketDataService(client)
    settings = Settings()
    strategy = LiquidMomentumStrategy(market, settings)
    assert strategy.name == "liquid_momentum"


def test_volatility_mispricing_strategy_init():
    """Test VolatilityMispricingStrategy initialization."""
    client = MockAlpacaClient()
    market = MarketDataService(client)
    settings = Settings()
    strategy = VolatilityMispricingStrategy(market, settings)
    assert strategy.name == "volatility_mispricing"


def test_mean_reversion_strategy_init():
    """Test MeanReversionStrategy initialization."""
    client = MockAlpacaClient()
    market = MarketDataService(client)
    settings = Settings()
    strategy = MeanReversionStrategy(market, settings)
    assert strategy.name == "mean_reversion"


def test_strategies_generate_signals_with_mock_data():
    """Test that strategies can generate signals with mock data."""
    # We'll use the MockAlpacaClient which returns predefined data
    client = MockAlpacaClient()
    market = MarketDataService(client)
    settings = Settings(
        underlyings="SPY",
        max_bid_ask_spread=0.25,  # Allow wider spreads for mock data
        min_open_interest=0,      # Allow zero open interest for mock data
        min_option_volume=0,      # Allow zero volume for mock data
        min_dte=0,
        max_dte=365,
        max_risk_per_trade=0.01,
        max_portfolio_exposure=0.2,
        max_positions=5,
        max_underlying_concentration=0.15,
        trading_enabled=True,
    )

    # Test each strategy
    strategies = [
        LiquidMomentumStrategy(market, settings),
        VolatilityMispricingStrategy(market, settings),
        MeanReversionStrategy(market, settings),
    ]

    market_state = {"underlyings": ["SPY"]}

    for strategy in strategies:
        signals = strategy.generate_signals(market_state)
        # We don't assert anything about the signals because the mock data may not trigger signals
        # We just want to ensure no exceptions are raised
        assert isinstance(signals, list)
        for signal in signals:
            assert hasattr(signal, 'underlying')
            assert hasattr(signal, 'direction')
            assert hasattr(signal, 'confidence')
            assert hasattr(signal, 'thesis')
            assert hasattr(signal, 'contract')
            assert hasattr(signal, 'timestamp')