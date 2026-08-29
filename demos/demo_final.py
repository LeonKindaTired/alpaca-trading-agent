from datetime import date, timedelta
from backend.app.config.settings import Settings
from backend.app.strategies.liquid_momentum import LiquidMomentumStrategy
from backend.backtesting.engine import BacktestEngine
from backend.app.data.mock_alpaca import MockAlpacaClient
from backend.app.data.market_data import MarketDataService
from backend.backtesting.metrics import PerformanceMetrics

print('Running final demonstration backtest...')
print('='*50)

# Create mock market data
client = MockAlpacaClient()
market_data = MarketDataService(client)

# Create settings
settings = Settings(
    underlyings='SPY,QQQ,IWM',
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

# Create strategy
strategy = LiquidMomentumStrategy(market_data, settings)

# Initialize backtest engine
backtest_engine = BacktestEngine(settings=settings)

# Run backtests for different periods
periods = [30, 60, 90, 180, 365]
results = []

for days in periods:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    try:
        result = backtest_engine.run_backtest(
            strategy=strategy,
            symbols=['SPY', 'QQQ', 'IWM'],
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000.0
        )
        results.append((days, result))
        print('{:3d} days: {:3d} trades, {:6.2%} return, {:5.2f} Sharpe'.format(days, result.total_trades, result.total_return, result.sharpe_ratio))
    except Exception as e:
        print('Error for {} days: {}'.format(days, e))

print('')
print('='*50)
print('DETAILED STATISTICAL SIGNIFICANCE ANALYSIS (90-day period)')
print('='*50)

# Run detailed analysis for 90-day period
end_date = date.today()
start_date = end_date - timedelta(days=90)

try:
    result = backtest_engine.run_backtest(
        strategy=strategy,
        symbols=['SPY', 'QQQ', 'IWM'],
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0
    )
    
    # Print enhanced performance report
    metrics = PerformanceMetrics.calculate_all(result)
    
    print('Initial Equity:     ${:,.2f}'.format(result.initial_equity))
    print('Final Equity:       ${:,.2f}'.format(result.final_equity))
    print('Total Return:       {:.2%}'.format(result.total_return))
    print('Annualized Return:  {:.2%}'.format(result.annualized_return))
    print('')
    print('Sharpe Ratio:       {:.2f}'.format(result.sharpe_ratio))
    if 'sharpe_ci_lower' in metrics:
        print('Sharpe 95% CI:      [{:.2f}, {:.2f}]'.format(metrics['sharpe_ci_lower'], metrics['sharpe_ci_upper']))
    print('Sortino Ratio:      {:.2f}'.format(result.sortino_ratio))
    print('Max Drawdown:       {:.2%}'.format(result.max_drawdown))
    print('Calmar Ratio:       {:.2f}'.format(metrics.get('calmar_ratio', 0.0)))
    print('')
    print('Total Trades:       {}'.format(result.total_trades))
    print('Winning Trades:     {}'.format(result.winning_trades))
    print('Losing Trades:      {}'.format(result.losing_trades))
    print('Win Rate:           {:.2%}'.format(result.win_rate))
    print('Profit Factor:      {:.2f}'.format(result.profit_factor))
    print('')
    if result.trades:
        returns = [t.pnl_percent for t in result.trades]
        print('Average Trade:      ${:,.2f}'.format(result.average_trade))
        print('Best Trade:         ${:,.2f}'.format(result.best_trade))
        print('Worst Trade:        ${:,.2f}'.format(result.worst_trade))
        print('Average Holding Period: {:.1f} days'.format(result.average_holding_period))
        print('')
        print('Return Std Dev:     {:.2%}'.format(metrics.get('return_std', 0.0)))
        print('Return 95% CI:      [{:.2%}, {:.2%}]'.format(metrics.get('return_ci_lower', 0.0), metrics.get('return_ci_upper', 0.0)))
        print('Return t-test p-value: {:.4f}'.format(metrics.get('return_ttest_pvalue', 1.0)))
        print('Return t-statistic:   {:.2f}'.format(metrics.get('return_tstat', 0.0)))
        
except Exception as e:
    print('Error: {}'.format(e))
    import traceback
    traceback.print_exc()
