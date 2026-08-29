from __future__ import annotations

from backend.app.config.settings import Settings
from backend.app.ai.supervisor import create_ai_supervisor

def test_ai_supervisor():
    settings = Settings()
    # Ensure AI is enabled
    settings.ai_enabled = True
    # Create AI supervisor
    ai_supervisor = create_ai_supervisor(settings)
    if ai_supervisor is None:
        print("AI supervisor is None (AI disabled or not configured)")
        return
    print(f"AI supervisor created: {type(ai_supervisor).__name__}")
    # We won't call evaluate because we don't have real data, but we can see if it's GeminiAI or MockAI
    if "Gemini" in type(ai_supervisor).__name__:
        print("Successfully created GeminiAI")
    else:
        print("Created MockAI (likely due to missing or invalid API key)")

if __name__ == "__main__":
    test_ai_supervisor()
