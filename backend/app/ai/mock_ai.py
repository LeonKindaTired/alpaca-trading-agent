from __future__ import annotations

import random
from typing import List

from backend.app.ai.base import AIInput, AIOutput, AISupervisor
from backend.app.data.models import Signal, OptionSnapshot


class MockAI(AISupervisor):
    """Mock AI implementation for testing and development.

    Returns deterministic outputs based on simple heuristics
    to allow testing of the AI integration without requiring
    an actual LLM API key.
    """

    def evaluate(self, input_data: AIInput) -> AIOutput:
        """Evaluate trading opportunity using enhanced mock logic.

        The mock AI now considers multiple factors to make more realistic decisions:
        - Signal direction and confidence
        - Technical indicators (RSI, momentum, volatility)
        - Options market conditions (if available)
        - Risk-adjusted returns
        """
        # If no signals, hold
        if not input_data.signals:
            return AIOutput(
                decision="HOLD",
                confidence=0.0,
                contract=None,
                thesis="No quantitative signals generated",
                expected_horizon="N/A",
                risk_factors=["No trading opportunity identified"],
                invalidation_conditions=["Signal generation required"]
            )

        # Process the first signal (in practice, we might want to evaluate all)
        signal = input_data.signals[0]

        # Start with signal's base confidence
        base_confidence = signal.confidence

        # Initialize decision factors
        long_score = 0.0
        short_score = 0.0

        # Factor 1: Signal direction (primary influence)
        if signal.direction == "long":
            long_score += base_confidence * 2.0  # Strong weight on signal direction
        else:
            short_score += base_confidence * 2.0

        # Factor 2: Technical indicators from features
        if input_data.features:
            rsi = input_data.features.get('rsi_14', 50.0)
            momentum_5 = input_data.features.get('momentum_5', 0.0)
            vol_change = input_data.features.get('volume_change_20', 0.0)
            price_to_sma20 = input_data.features.get('price_to_sma20', 0.0)

            # RSI considerations (avoid overbought/oversold extremes)
            if rsi > 70:  # Overbought - favors short
                short_score += 0.3
                long_score -= 0.2
            elif rsi < 30:  # Oversold - favors long
                long_score += 0.3
                short_score -= 0.2

            # Momentum confirmation
            if momentum_5 > 0.02:  # Strong positive momentum
                long_score += 0.4
            elif momentum_5 < -0.02:  # Strong negative momentum
                short_score += 0.4

            # Volume confirmation
            if vol_change > 0.3:  # High volume increase
                if signal.direction == "long":
                    long_score += 0.2
                else:
                    short_score += 0.2

            # Price relative to SMA
            if price_to_sma20 > 0.05:  # Price above SMA
                long_score += 0.1
            elif price_to_sma20 < -0.05:  # Price below SMA
                short_score += 0.1

        # Factor 3: Options market conditions (if available)
        if input_data.options and len(input_data.options) > 0:
            options_snapshot = input_data.options[0]
            if options_snapshot and options_snapshot.implied_volatility is not None:
                iv = options_snapshot.implied_volatility
                # High IV suggests higher uncertainty - reduce confidence
                if iv > 0.5:  # Very high IV (>50%)
                    long_score *= 0.8
                    short_score *= 0.8
                elif iv > 0.3:  # Moderately high IV
                    long_score *= 0.9
                    short_score *= 0.9

                # Consider delta for directional bias
                if options_snapshot.greeks and options_snapshot.greeks.delta is not None:
                    delta = options_snapshot.greeks.delta
                    # For calls: delta > 0, for puts: delta < 0
                    # If we're signaling long (call), positive delta is good
                    # If we're signaling short (put), negative delta is good
                    if signal.direction == "long" and delta > 0.3:
                        long_score += 0.2
                    elif signal.direction == "short" and delta < -0.3:
                        short_score += 0.2

        # Factor 4: Risk-adjusted consideration
        # Penalize extremely high confidence as it might be overfitting
        if base_confidence > 0.9:
            long_score *= 0.9
            short_score *= 0.9

        # Make decision based on scores
        if long_score > short_score and long_score > 0.3:
            decision = "BUY"
            confidence = min(0.95, long_score)
        elif short_score > long_score and short_score > 0.3:
            decision = "SELL"
            confidence = min(0.95, short_score)
        else:
            decision = "HOLD"
            confidence = 0.0

        # Enhance thesis based on decision and factors considered
        if decision == "HOLD":
            thesis = f"AI analysis: Signal insufficiently convincing after considering technical factors (RSI: {input_data.features.get('rsi_14', 'N/A'):.1f}, Momentum: {input_data.features.get('momentum_5', 0):.2%})"
        else:
            thesis = f"AI analysis: {signal.direction} signal enhanced by technical confirmation (RSI: {input_data.features.get('rsi_14', 'N/A'):.1f}, 5-day momentum: {input_data.features.get('momentum_5', 0):.2%})"

        # Determine expected horizon based on volatility and momentum
        expected_horizon = "1-5 days"  # Default
        if input_data.features:
            volatility = input_data.features.get('realized_volatility_20', 0.0)
            if volatility > 0.03:  # High volatility
                expected_horizon = "1-3 days"
            elif volatility < 0.01:  # Low volatility
                expected_horizon = "1-2 weeks"

        # Risk factors (enhanced)
        risk_factors = []
        if input_data.features:
            rsi = input_data.features.get('rsi_14', 50.0)
            if rsi > 70:
                risk_factors.append("RSI indicates overbought conditions")
            elif rsi < 30:
                risk_factors.append("RSI indicates oversold conditions")

            volatility = input_data.features.get('realized_volatility_20', 0.0)
            if volatility > 0.04:
                risk_factors.append("High realized volatility increases uncertainty")

            vol_change = input_data.features.get('volume_change_20', 0.0)
            if abs(vol_change) > 0.5:
                risk_factors.append("Unusual volume activity detected")

        if not input_data.options:
            risk_factors.append("Limited options data for detailed analysis")

        # Invalidation conditions (enhanced)
        invalidation_conditions = [
            "Signal momentum reverses",
            "RSI moves to extreme levels (>80 or <20)",
            "Market volatility increases significantly (>50% above current)",
            "Unexpected news event affecting underlying",
            "Options IV increases by >30% suggesting heightened uncertainty"
        ]

        return AIOutput(
            decision=decision,
            confidence=confidence,
            contract=signal.contract if decision in ["BUY", "SELL"] else None,
            thesis=thesis,
            expected_horizon=expected_horizon,
            risk_factors=risk_factors,
            invalidation_conditions=invalidation_conditions
        )