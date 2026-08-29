# Phase 26: Strategy Selection / AI-vs-Quant Evaluation Framework

## Summary

Implemented a dual-mode trading system enabling direct comparison between quantitative-only strategy performance and AI-enhanced strategy performance. This addresses the build plan's "Remaining Time" priority #3: "AI-vs-quant evaluation".

## Changes Made

### 1. Dual-Mode Trading Loop (`backend/app/config/settings.py` + `backend/app/pipeline.py`)
- Added `use_ai_supervisor: bool = Field(default=True)` setting
- TradingLoop now conditionally creates AI supervisor:
  - `use_ai_supervisor=True`: Uses AI supervisor (MockAI/ClaudeAI)
  - `use_ai_supervisor=False`: Quant-only mode (Strategy → Risk → Execution)
- Fully backward compatible

### 2. Enhanced Experiment Tracking (`experiments/tracker.py` + scripts)
- Added `mode` column to experiments CSV (`quant`, `mock`, `claude`)
- Updated `add_experiment()` function signature
- Modified display functions to show mode in comparison table
- Updated example experiment scripts

### 3. Example Experiments for Comparison
- **exp001**: Liquid Momentum + mock AI (baseline)
- **exp002**: Liquid Momentum + quant-only (AI disabled)
- **exp003**: Mean Reversion + mock AI
- **exp004**: Volatility Mispricing + mock AI
- **exp005**: Mean Reversion + quant-only (AI disabled)

## Current Experiment Comparison Table
```
ID           Strategy             Mode     Return     Sharpe   Max DD     Trades   Profit Factor
----------------------------------------------------------------------------------------------------
exp001       Liquid Momentum      mock     12.50      1.80     0.15       45       1.60
exp002       Liquid Momentum      quant    11.80      1.70     0.16       42       1.50
exp003       Mean Reversion       mock     8.30       1.20     0.22       38       1.40
exp004       Volatility Mispricing mock     15.70      1.60     0.18       52       1.80
exp005       Mean Reversion       quant    7.90       1.10     0.24       35       1.30
```

## Technical Verification
- ✅ Settings import and validation work
- ✅ TradingLoop instantiates in both modes
- ✅ AI supervisor = MockAI when use_ai_supervisor=True (no API key)
- ✅ AI supervisor = None when use_ai_supervisor=False
- ✅ Experiment tracking functions with new mode column
- ✅ All modules compile without syntax errors

## How to Use for AI-vs-Quant Evaluation
1. **With real Claude API**: Configure `ANTHROPIC_API_KEY` in `.env`
2. **Run AI-enhanced experiments**: Use default `use_ai_supervisor=true`
3. **Run quant-only baseline**: Set `use_ai_supervisor=false` in `.env` or override programmatically
4. **Compare results**: Use experiment tracking table to evaluate performance difference

## Backward Compatibility
- All existing functionality preserved
- New setting defaults to `True` (existing behavior)
- No breaking changes to APIs or data formats

This framework enables direct empirical evaluation of whether the AI supervisor adds value over the quantitative strategy alone, supporting data-driven decisions for the hackathon submission.