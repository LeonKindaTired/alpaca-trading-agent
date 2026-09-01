from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.logging import setup_logging
from backend.app.config.settings import get_settings
from backend.app.dashboard_api import router as dashboard_router

settings = get_settings()
setup_logging(settings.log_level)
app = FastAPI(title="Alpaca Trading Agent", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include dashboard API router
app.include_router(dashboard_router)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "trading_enabled": settings.trading_enabled,
        "paper": settings.alpaca_paper,
        "underlyings": settings.underlying_list,
    }