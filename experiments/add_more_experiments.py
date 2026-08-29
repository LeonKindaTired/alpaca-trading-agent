import sys
sys.path.insert(0, '.')
from tracker import add_experiment

# Experiment 3: Mean Reversion with Mock AI
add_experiment(
    experiment_id="exp003",
    strategy="Mean Reversion",
    mode="mock",
    parameters="{'zscore_threshold': 2.0, 'lookback': 20}",
    dataset="SPY 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=8.3,
    sharpe=1.2,
    max_drawdown=0.22,
    trade_count=38,
    profit_factor=1.4,
    notes="Testing mean reversion on SPY with z-score threshold 2.0 using mock AI"
)

# Experiment 4: Volatility Mispricing with Mock AI
add_experiment(
    experiment_id="exp004",
    strategy="Volatility Mispricing",
    mode="mock",
    parameters="{'iv_rv_threshold': 0.05, 'min_iv': 0.1}",
    dataset="QQQ 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=15.7,
    sharpe=1.6,
    max_drawdown=0.18,
    trade_count=52,
    profit_factor=1.8,
    notes="Testing volatility mispricing on QQQ using mock AI"
)

# Experiment 5: Mean Reversion Quant-Only
add_experiment(
    experiment_id="exp005",
    strategy="Mean Reversion",
    mode="quant",
    parameters="{'zscore_threshold': 2.0, 'lookback': 20}",
    dataset="SPY 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=7.9,
    sharpe=1.1,
    max_drawdown=0.24,
    trade_count=35,
    profit_factor=1.3,
    notes="Mean reversion with AI supervisor disabled (quant-only mode)"
)

print("Added experiments exp003, exp004, exp005")