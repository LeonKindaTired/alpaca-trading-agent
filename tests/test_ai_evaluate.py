from __future__ import annotations

from backend.app.config.settings import Settings
from backend.app.ai.supervisor import create_ai_supervisor
from backend.app.ai.base import AIInput
from backend.app.data.models import Signal, OptionSnapshot

def test_ai_evaluate():
    settings = Settings()
    settings.ai_enabled = True
    ai_supervisor = create_ai_supervisor(settings)
    if ai_supervisor is None:
        print("AI supervisor is None")
        return

    print(f"AI supervisor: {type(ai_supervisor).__name__}")

    # Create minimal AIInput
    input_data = AIInput(
        underlying="SPY",
        price=500.0,
        features={},
        signals=[],  # No signals
        options=[],
        portfolio={},
        risk={}
    )

    try:
        output = ai_supervisor.evaluate(input_data)
        print(f"AI decision: {output.decision}")
        print(f"Confidence: {output.confidence}")
        print(f"Thesis: {output.thesis}")
    except Exception as e:
        print(f"Error during AI evaluation: {e}")

if __name__ == "__main__":
    test_ai_evaluate()
