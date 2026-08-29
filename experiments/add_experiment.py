import sys
sys.path.insert(0, '.')
from tracker import add_experiment

if __name__ == "__main__":
    # Example experiment
    add_experiment(
        experiment_id="exp001",
        strategy="Liquid Momentum",
        parameters="{'lookback': 20, 'threshold': 0.02}",
        dataset="SPY 1h bars",
        period="2024-01-01 to 2024-08-01",
        return_val=12.5,
        sharpe=1.8,
        max_drawdown=0.15,
        trade_count=45,
        profit_factor=1.6,
        notes="Initial test with liquid momentum"
    )
    print("Experiment exp001 added.")