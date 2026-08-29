import csv
import os
from datetime import datetime

EXPERIMENTS_FILE = os.path.join(os.path.dirname(__file__), 'experiments.csv')

def init_experiments_file():
    """Create the experiments CSV file with header if it doesn't exist."""
    if not os.path.exists(EXPERIMENTS_FILE):
        with open(EXPERIMENTS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'experiment_id',
                'strategy',
                'mode',  # e.g., 'quant', 'ai', 'mock'
                'parameters',
                'dataset',
                'period',
                'return',
                'sharpe',
                'max_drawdown',
                'trade_count',
                'profit_factor',
                'notes'
            ])

def add_experiment(experiment_id, strategy, mode, parameters, dataset, period,
                   return_val, sharpe, max_drawdown, trade_count, profit_factor, notes):
    """Add a new experiment to the CSV."""
    init_experiments_file()
    with open(EXPERIMENTS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            experiment_id,
            strategy,
            mode,
            parameters,
            dataset,
            period,
            return_val,
            sharpe,
            max_drawdown,
            trade_count,
            profit_factor,
            notes
        ])

def list_experiments():
    """List all experiments."""
    init_experiments_file()
    if not os.path.exists(EXPERIMENTS_FILE):
        return []
    with open(EXPERIMENTS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)

def print_experiments():
    """Print experiments in a simple table."""
    experiments = list_experiments()
    if not experiments:
        print("No experiments recorded.")
        return

    # Print header
    headers = ['ID', 'Strategy', 'Mode', 'Return', 'Sharpe', 'Max DD', 'Trades', 'Profit Factor']
    print(f"{'ID':<12} {'Strategy':<20} {'Mode':<8} {'Return':<10} {'Sharpe':<8} {'Max DD':<10} {'Trades':<8} {'Profit Factor':<12}")
    print("-" * 100)
    for exp in experiments:
        print(f"{exp['experiment_id']:<12} {exp['strategy']:<20} {exp['mode']:<8} {float(exp['return']):<10.2f} {float(exp['sharpe']):<8.2f} {float(exp['max_drawdown']):<10.2f} {exp['trade_count']:<8} {float(exp['profit_factor']):<12.2f}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print_experiments()
    else:
        print("Usage: python tracker.py list")
        print("To add an experiment, import the add_experiment function.")