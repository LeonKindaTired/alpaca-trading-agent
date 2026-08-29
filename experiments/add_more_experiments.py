import sys
sys.path.insert(0, '.')
from tracker import add_experiment

# Experiment 2: Mean Reversion (example)
add_experiment(
    experiment_id="exp002",
    strategy="Mean Reversion",
    parameters="{'zscore_threshold': 2.0, 'lookback': 20}",
    dataset="SPY 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=8.3,
    sharpe=1.2,
    max_drawdown=0.22,
    trade_count=38,
    profit_factor=1.4,
    notes="Testing mean reversion on SPY with z-score threshold 2.0"
)

# Experiment 3: Volatility Mispricing (example)
add_experiment(
    experiment_id="exp003",
    strategy="Volatility Mispricing",
    parameters="{'iv_rv_threshold': 0.05, 'min_iv': 0.1}",
    dataset="QQQ 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=15.7,
    sharpe=1.6,
    max_drawdown=0.18,
    trade_count=52,
    profit_factor=1.8,
    notes="Testing volatility mispricing on QQQ"
)

# Experiment 4: Liquid Momentum with different parameters
add_experiment(
    experiment_id="exp004",
    strategy="Liquid Momentum",
    parameters="{'lookback': 10, 'threshold': 0.005}",
    dataset="IWM 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=10.2,
    sharpe=1.4,
    max_drawdown=0.20,
    trade_count=45,
    profit_factor=1.5,
    notes="Testing liquid momentum on IWM with shorter lookback"
)

print("Added experiments exp002, exp003, exp004")