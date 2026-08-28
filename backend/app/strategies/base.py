from abc import ABC, abstractmethod

from backend.app.data.models import Signal


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_signals(self, market_state: dict) -> list[Signal]:
        ...
