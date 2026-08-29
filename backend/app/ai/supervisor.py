from __future__ import annotations

from typing import Optional

from backend.app.ai.base import AISupervisor
from backend.app.ai.claude_ai import ClaudeAI
from backend.app.ai.mock_ai import MockAI
from backend.app.config.settings import Settings


def create_ai_supervisor(settings: Settings) -> Optional[AISupervisor]:
    """Factory function to create the appropriate AI supervisor.

    Returns:
        AISupervisor instance (ClaudeAI or MockAI) or None if AI is disabled
        or not properly configured.
    """
    # Check if AI is enabled in settings
    if not getattr(settings, 'ai_enabled', False):
        return None

    # Try to create ClaudeAI if API key is available
    try:
        # Check if we have a valid API key
        api_key = getattr(settings, 'anthropic_api_key', '')
        if api_key and not api_key.startswith("your_"):
            return ClaudeAI(settings)
    except Exception:
        # If ClaudeAI creation fails, fall back to mock or return None
        pass

    # Fall back to MockAI for development/testing
    try:
        return MockAI(settings)
    except Exception:
        # If both fail, return None (AI disabled)
        return None