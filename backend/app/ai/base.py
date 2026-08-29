from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from backend.app.data.models import Signal, OptionSnapshot
from backend.app.data.client import AlpacaClient
from backend.app.config.settings import Settings


@dataclass
class AIInput:
    """Structured input to the AI supervisor."""
    underlying: str
    price: float
    features: dict
    signals: List[Signal]
    options: List[OptionSnapshot]
    portfolio: dict  # Simplified portfolio state
    risk: dict       # Risk assessment context


@dataclass
class AIOutput:
    """Structured output from the AI supervisor."""
    decision: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0
    contract: Optional[str]
    thesis: str
    expected_horizon: str
    risk_factors: List[str]
    invalidation_conditions: List[str]


class AISupervisor(ABC):
    """Abstract base case for AI supervisor implementations."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def evaluate(self, input_data: AIInput) -> AIOutput:
        """Evaluate trading opportunity and return structured decision.

        Args:
            input_data: Structured input containing market data, signals, etc.

        Returns:
            AIOutput with decision, confidence, and reasoning
        """
        pass

    def validate_output(self, output: AIOutput) -> bool:
        """Validate AI output conforms to expected schema and constraints.

        Returns:
            True if output is valid, False otherwise
        """
        # Check decision is valid
        if output.decision not in ["BUY", "SELL", "HOLD"]:
            return False

        # Check confidence is in valid range
        if not 0.0 <= output.confidence <= 1.0:
            return False

        # If decision is BUY or SELL, contract should be provided
        if output.decision in ["BUY", "SELL"] and not output.contract:
            return False

        # If decision is HOLD, contract should be None
        if output.decision == "HOLD" and output.contract is not None:
            return False

        return True