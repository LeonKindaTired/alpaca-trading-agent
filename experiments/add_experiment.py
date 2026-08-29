import sys
sys.path.insert(0, '.')
from tracker import add_experiment

# Example experiments with mode specified

# Experiment 1: Liquid Momentum with Mock AI (since no API key)
add_experiment(
    experiment_id="exp001",
    strategy="Liquid Momentum",
    mode="mock",
    parameters="{'lookback': 20, 'threshold': 0.02}",
    dataset="SPY 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=12.5,
    sharpe=1.8,
    max_drawdown=0.15,
    trade_count=45,
    profit_factor=1.6,
    notes="Initial test with liquid momentum using mock AI"
)

# Experiment 2: Liquid Momentum Quant-Only (AI supervisor disabled)
add_experiment(
    experiment_id="exp002",
    strategy="Liquid Momentum",
    mode="quant",
    parameters="{'lookback': 20, 'threshold': 0.02}",
    dataset="SPY 1h bars",
    period="2024-01-01 to 2024-08-01",
    return_val=11.8,
    sharpe=1.7,
    max_drawdown=0.16,
    trade_count=42,
    profit_factor=1.5,
    notes="Liquid momentum with AI supervisor disabled (quant-only mode)"
)

print("Added experiments exp001 (mock AI) and exp002 (quant-only)")