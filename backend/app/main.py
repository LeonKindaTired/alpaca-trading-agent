from fastapi import FastAPI

from backend.app.config.logging import setup_logging
from backend.app.config.settings import get_settings

settings = get_settings()
setup_logging(settings.log_level)
app = FastAPI(title="Alpaca Trading Agent", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "trading_enabled": settings.trading_enabled,
        "paper": settings.alpaca_paper,
        "underlyings": settings.underlying_list,
    }
