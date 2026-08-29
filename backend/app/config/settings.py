from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True

    trading_enabled: bool = True
    anthropic_api_key: str = ""

    max_risk_per_trade: float = 0.01
    max_portfolio_exposure: float = 0.20
    max_daily_loss: float = 0.02
    max_drawdown: float = 0.08
    max_positions: int = 3
    max_underlying_concentration: float = 0.15
    max_bid_ask_spread: float = 0.08
    min_option_volume: int = 10
    min_open_interest: int = 50
    min_dte: int = 3
    max_dte: int = 45
    loop_interval_seconds: int = 60

    underlyings: str = "SPY,QQQ,IWM"
    database_path: str = "data/agent.db"
    log_level: str = "INFO"

    dry_run: bool = Field(default=False)
    ai_enabled: bool = Field(default=False)

    # AI-specific parameters
    ai_temperature: float = Field(default=0.3)
    ai_max_tokens: int = Field(default=1000)
    ai_model: str = Field(default="claude-3-5-sonnet-20241022")

    @property
    def underlying_list(self) -> list[str]:
        return [s.strip().upper() for s in self.underlyings.split(",") if s.strip()]


def get_settings() -> Settings:
    return Settings()
