from __future__ import annotations

import json
import os
from typing import List, Optional

import anthropic
from pydantic import BaseModel, Field, ValidationError

from backend.app.ai.base import AIInput, AIOutput, AISupervisor
from backend.app.data.models import Signal, OptionSnapshot


class AIResponseSchema(BaseModel):
    """Pydantic schema for validating AI response."""
    decision: str = Field(..., pattern="^(BUY|SELL|HOLD)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    contract: Optional[str] = None
    thesis: str = Field(..., min_length=10)
    expected_horizon: str = Field(..., min_length=1)
    risk_factors: List[str] = Field(default_factory=list)
    invalidation_conditions: List[str] = Field(default_factory=list)


class ClaudeAI(AISupervisor):
    """Real AI implementation using Anthropic's Claude API."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
        if not api_key or api_key.startswith("your_"):
            raise ValueError(
                "Valid ANTHROPIC_API_KEY required for ClaudeAI implementation. "
                "Set in .env file or provide via settings."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"  # Latest available model

    def _create_prompt(self, input_data: AIInput) -> str:
        """Create a structured prompt for the AI supervisor."""
        # Format signals for the prompt
        signals_text = ""
        if input_data.signals:
            for i, signal in enumerate(input_data.signals[:3]):  # Limit to top 3 signals
                signals_text += f"""
Signal {i+1}:
  Underlying: {signal.underlying}
  Direction: {signal.direction}
  Confidence: {signal.confidence:.2f}
  Thesis: {signal.thesis}
  Expected Edge: {signal.expected_edge:.2%}
  Contract: {signal.contract or 'None'}
"""
        else:
            signals_text = "No signals generated"

        # Format options data (limit to avoid token overflow)
        options_text = ""
        if input_data.options:
            options_text = f"Available options contracts: {len(input_data.options)} contracts\n"
            # Show first few options with key details
            for i, opt in enumerate(input_data.options[:3]):
                options_text += f"""
Option {i+1}:
  Symbol: {opt.contract.symbol}
  Underlying: {opt.contract.underlying}
  Strike: {opt.contract.strike}
  Expiration: {opt.contract.expiration}
  Type: {'Call' if opt.contract.right == 'call' else 'Put'}
  Bid: {opt.quote.bid if opt.quote else 'N/A'}
  Ask: {opt.quote.ask if opt.quote else 'N/A'}
  Mid: {opt.quote.mid if opt.quote else 'N/A'}
  IV: {opt.iv:.2%} if opt.iv else 'N/A'
  Delta: {opt.delta:.3f} if opt.delta else 'N/A'
  Volume: {opt.volume or 'N/A'}
  Open Interest: {opt.open_interest or 'N/A'}
"""
        else:
            options_text = "No options data available"

        # Format portfolio info
        portfolio_text = ""
        if input_data.portfolio:
            portfolio_text = f"""
Portfolio State:
  Equity: {input_data.portfolio.get('equity', 'N/A')}
  Buying Power: {input_data.portfolio.get('buying_power', 'N/A')}
  Positions Count: {len(input_data.portfolio.get('positions', []))}
  Daily P&L: {input_data.portfolio.get('daily_pnl', 'N/A')}
"""
        else:
            portfolio_text = "No portfolio data available"

        # Format risk context
        risk_text = ""
        if input_data.risk:
            risk_text = f"""
Risk Context:
  Max Risk Per Trade: {input_data.risk.get('max_risk_per_trade', 'N/A')}
  Max Portfolio Exposure: {input_data.risk.get('max_portfolio_exposure', 'N/A')}
  Current Exposure: {input_data.risk.get('current_exposure', 'N/A')}
"""
        else:
            risk_text = "No risk context available"

        # Format features in a more readable way
        features_text = ""
        if input_data.features:
            features_text = "Technical Indicators:\n"
            # Group related features for better readability
            price_features = {k: v for k, v in input_data.features.items() if 'price' in k or 'sma' in k or 'ema' in k}
            momentum_features = {k: v for k, v in input_data.features.items() if 'momentum' in k}
            volatility_features = {k: v for k, v in input_data.features.items() if 'vol' in k or 'atr' in k}
            other_features = {k: v for k, v in input_data.features.items() if k not in price_features and k not in momentum_features and k not in volatility_features}

            if price_features:
                features_text += "  Price/Moving Averages:\n"
                for k, v in price_features.items():
                    features_text += f"    {k}: {v:.4f}\n"

            if momentum_features:
                features_text += "  Momentum:\n"
                for k, v in momentum_features.items():
                    features_text += f"    {k}: {v:.2%}\n"

            if volatility_features:
                features_text += "  Volatility:\n"
                for k, v in volatility_features.items():
                    if 'rsi' in k:
                        features_text += f"    {k}: {v:.1f}\n"
                    else:
                        features_text += f"    {k}: {v:.2%}\n"

            if other_features:
                features_text += "  Other:\n"
                for k, v in other_features.items():
                    features_text += f"    {k}: {v}\n"
        else:
            features_text = "No features available"

        # Build the prompt
        prompt_parts = [
            "You are an AI trading supervisor for an options trading agent. Your role is to evaluate quantitative trading signals and provide reasoned trading decisions.",
            "",
            "MARKET DATA:",
            f"Underlying: {input_data.underlying}",
            f"Current Price: {input_data.price:.2f}",
            "",
            "FEATURES:",
            features_text,
            "",
            "QUANTITATIVE SIGNALS:",
            signals_text,
            "",
            "OPTIONS DATA:",
            options_text,
            "",
            "PORTFOLIO & RISK CONTEXT:",
            portfolio_text,
            risk_text,
            "",
            "TASK:",
            "Evaluate the quantitative signal(s) above and provide a trading decision. Consider:",
            "1. Does the signal make technical sense given the market data and features?",
            "2. Is the opportunity consistent with current market conditions (consider RSI, momentum, volatility)?",
            "3. What are the key risks and invalidation conditions (especially from volatility and volume signals)?",
            "4. What is your confidence in this trade (0.0-1.0)?",
            "5. What is the expected holding period based on volatility and market conditions?",
            "",
            "You MUST return a valid JSON object that conforms to the following schema exactly:",
            "{",
            '  "decision": "BUY" | "SELL" | "HOLD",',
            '  "confidence": float between 0.0 and 1.0,',
            '  "contract": string (option symbol) or null (required if decision is BUY/SELL),',
            '  "thesis": string (explanation of why this trade makes sense),',
            '  "expected_horizon": string (expected holding period, e.g., "1-3 days", "1-2 weeks"),',
            '  "risk_factors": [list of strings describing key risks],',
            '  "invalidation_conditions": [list of strings describing what would invalidate this trade]',
            "}",
            "",
            "If you decide HOLD, set contract to null and provide explanation in thesis.",
            "If you decide BUY or SELL, you MUST provide a valid contract symbol.",
            "Provide a concise but complete thesis explaining your reasoning, referencing specific technical indicators.",
            "List specific, actionable risk factors and invalidation conditions based on market data.",
            "",
            "Respond ONLY with the JSON object, no additional text or explanation."
        ]

        return "\n".join(prompt_parts)

    def evaluate(self, input_data: AIInput) -> AIOutput:
        """Evaluate trading opportunity using Claude AI."""
        try:
            prompt = self._create_prompt(input_data)

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,  # Low temperature for more consistent outputs
                system="You are an expert options trading AI supervisor. You analyze quantitative signals, market data, and risk factors to provide reasoned trading decisions. Always respond with valid JSON only.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract the response text
            response_text = message.content[0].text.strip()

            # Try to parse as JSON
            try:
                # Clean up the response in case there's extra text
                if response_text.startswith("```json"):
                    response_text = response_text.split("```json")[1]
                if response_text.endswith("```"):
                    response_text = response_text.rsplit("```", 1)[0]
                response_text = response_text.strip()

                # Parse JSON
                response_data = json.loads(response_text)

                # Validate with Pydantic schema
                validated = AIResponseSchema(**response_data)

                # Convert to our AIOutput format
                return AIOutput(
                    decision=validated.decision,
                    confidence=validated.confidence,
                    contract=validated.contract,
                    thesis=validated.thesis,
                    expected_horizon=validated.expected_horizon,
                    risk_factors=validated.risk_factors,
                    invalidation_conditions=validated.invalidation_conditions
                )

            except (json.JSONDecodeError, ValidationError) as e:
                # If JSON parsing or validation fails, return a safe HOLD decision
                return AIOutput(
                    decision="HOLD",
                    confidence=0.0,
                    contract=None,
                    thesis=f"AI output validation failed: {str(e)}. Defaulting to HOLD for safety.",
                    expected_horizon="N/A",
                    risk_factors=["AI output format invalid"],
                    invalidation_conditions=["AI system error"]
                )

        except Exception as e:
            # If API call fails, return safe HOLD decision
            return AIOutput(
                decision="HOLD",
                confidence=0.0,
                contract=None,
                thesis=f"AI service unavailable: {str(e)}. Defaulting to HOLD for safety.",
                expected_horizon="N/A",
                risk_factors=["AI service error"],
                invalidation_conditions=["AI system unavailable"]
            )