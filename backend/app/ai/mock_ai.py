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
        """Evaluate trading opportunity using mock logic.

        For mock implementation, we'll:
        - If there are no signals, return HOLD
        - If signals exist, check if momentum is strong enough
        - Return BUY for positive momentum, SELL for negative
        - Confidence based on signal strength
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

        # Simple mock logic based on signal direction and confidence
        if signal.confidence > 0.7:
            # High confidence signal - follow the signal
            if signal.direction == "long":
                decision = "BUY"
            else:  # short
                decision = "SELL"
            confidence = min(0.95, signal.confidence + 0.1)
            thesis = f"High confidence {signal.direction} signal confirmed by AI analysis"
        elif signal.confidence > 0.4:
            # Medium confidence - AI adds some validation
            if signal.direction == "long":
                decision = "BUY"
            else:
                decision = "SELL"
            confidence = signal.confidence
            thesis = f"Medium confidence {signal.direction} signal validated by AI"
        else:
            # Low confidence - AI recommends holding
            decision = "HOLD"
            confidence = 0.0
            contract = None
            thesis = f"Low confidence signal ({signal.confidence:.2f}) rejected by AI"
            return AIOutput(
                decision=decision,
                confidence=confidence,
                contract=contract,
                thesis=thesis,
                expected_horizon="N/A",
                risk_factors=["Low signal confidence"],
                invalidation_conditions=["Signal strength insufficient"]
            )

        # Determine expected horizon based on signal characteristics
        expected_horizon = "1-5 days"  # Default

        # Risk factors (simplified)
        risk_factors = []
        if signal.confidence < 0.6:
            risk_factors.append("Moderate signal confidence")
        if not input_data.options:
            risk_factors.append("Limited options data available")

        # Invalidation conditions
        invalidation_conditions = [
            "Signal momentum reverses",
            "Market volatility increases significantly",
            "Unexpected news event affecting underlying"
        ]

        return AIOutput(
            decision=decision,
            confidence=confidence,
            contract=signal.contract,
            thesis=thesis,
            expected_horizon=expected_horizon,
            risk_factors=risk_factors,
            invalidation_conditions=invalidation_conditions
        )