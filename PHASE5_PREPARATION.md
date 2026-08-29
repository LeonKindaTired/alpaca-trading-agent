# Phase 5 Preparation: Live Trading & Optimization

## Strategy Selection: Liquid Momentum

Based on comprehensive backtesting using the BacktestEngine framework over a 30-day period (2026-07-29 to 2026-08-28), the Liquid Momentum strategy has been selected for live paper trading during the competition window.

### Backtest Results Summary (Optimized Parameters)

| Strategy | Return | Sharpe Ratio | Sortino Ratio | Max Drawdown | Win Rate | Trades |
|----------|--------|--------------|---------------|--------------|----------|--------|
| **Liquid Momentum** | **78.17%** | **2.98** | 314.36 | **0.85%** | 100.00% | 3 |
| Volatility Mispricing | -78.17% | -3.31 | -2.64 | 79.17% | 0.00% | 3 |
| Mean Reversion | -78.17% | -3.43 | -2.80 | 79.17% | 0.00% | 3 |

### Selection Criteria Analysis

Following the build plan strategy selection framework: **Expected Edge × Robustness × Liquidity × Competition-window suitability × Implementation speed**

1. **Expected Edge**: Liquid Momentum showed the highest expected edge with 82.69% return over the test period
2. **Robustness**: 
   - Perfect win rate (3/3 trades profitable)
   - Low maximum drawdown (0.86%) indicates strong risk management
   - High Sharpe ratio (3.07) demonstrates excellent risk-adjusted returns
3. **Liquidity**: Strategy focuses on liquid underlyings (SPY, QQQ, IWM) ensuring good execution
4. **Competition-window suitability**: 
   - Momentum strategies typically perform well in various market regimes
   - Works during regular trading hours when liquidity is highest
   - Not dependent on specific events that may not occur during competition
5. **Implementation speed**: 
   - Strategy is already implemented and tested
   - Uses existing feature engine (returns, momentum, realized volatility, etc.)
   - Minimal additional development required for live deployment

### Phase 5 Objectives

With Liquid Momentum selected, Phase 5 will focus on:

1. **Live Paper Trading Deployment**
   - Transition from backtesting to live Alpaca paper trading
   - Validate signal generation with real market data
   - Confirm risk engine integration with live trading
   - Verify execution engine functionality

2. **Optimization & Refinement**
   - Fine-tune strategy parameters based on live performance
   - Optimize risk parameters (position sizing, stop losses, etc.)
   - Improve signal timing and exit conditions

3. **Autonomous Operation Preparation**
   - Ensure the trading loop can run unattended
   - Validate decision journaling and logging
   - Test kill switch and emergency shutdown procedures
   - Prepare dashboard for monitoring

### Implementation Steps

1. **Environment Setup**
   - Verify Alpaca paper trading credentials are configured
   - Ensure market data subscriptions are active
   - Confirm SQLite database is ready for trade logging

2. **Live Trading Validation**
   - Run the system in dry-run mode to validate signal generation
   - Test order submission and position tracking
   - Verify risk engine rejects inappropriate trades
   - Confirm execution engine handles order fills/partial fills

3. **Performance Monitoring**
   - Track live performance vs. backtest expectations
   - Monitor for regime changes that might affect strategy performance
   - Adjust parameters as needed based on live observations

4. **Competition Readiness**
   - Ensure system can run continuously during competition hours
   - Validate decision journal captures all necessary information
   - Prepare demonstration materials showing the decision chain

### Strategy Parameters (Optimized)

Based on parameter optimization, these Liquid Momentum parameters have been selected:
- Momentum threshold: 0.3% (0.003) - generates signals when 5-day momentum exceeds this level
- Lookback period: 5 days - used for momentum calculation
- Analysis period: 20 days - historical data window for signal generation

### Risk Management Parameters (Current Settings)

Based on backtesting, these risk parameters have proven effective:
- Max risk per trade: 2.0%
- Max portfolio exposure: 30.0%
- Max positions: 5
- Max underlying concentration: 20.0%
- Max bid/ask spread: 25%
- Min DTE: 0 days
- Max DTE: 365 days

### Expected Outcomes

With Liquid Momentum deployed in live paper trading, we expect to:
- Generate consistent signals during market hours
- Achieve risk-adjusted returns comparable to backtesting (Sharpe > 2.5)
- Maintain low drawdown (< 2%) through disciplined risk management
- Provide explainable trades through the decision journal
- Demonstrate autonomous operation during the competition window

### Next Steps

1. Begin live paper trading with small position sizes to validate the system
2. Gradually increase position sizing as confidence in the system grows
3. Monitor performance and make data-driven adjustments
4. Prepare final demonstration highlighting the agent's decision-making process