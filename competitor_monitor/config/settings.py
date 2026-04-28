from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SKUConfig(BaseModel):
    id: str
    name: str
    url: str
    price_alert_threshold_pct: float = 5.0  # alert when price shifts by ≥ this %


class CompetitorConfig(BaseModel):
    id: str
    name: str
    market: str  # ISO country code: DE, PL, NL, AT, BE
    base_url: str
    homepage_url: str
    skus: list[SKUConfig] = Field(default_factory=list)


class MarketConfig(BaseModel):
    code: str   # ISO country code
    language: str  # BCP-47 language tag
    currency: str  # ISO 4217


MARKETS: dict[str, MarketConfig] = {
    "DE": MarketConfig(code="DE", language="de", currency="EUR"),
    "PL": MarketConfig(code="PL", language="pl", currency="PLN"),
    "NL": MarketConfig(code="NL", language="nl", currency="EUR"),
    "AT": MarketConfig(code="AT", language="de", currency="EUR"),
    "BE": MarketConfig(code="BE", language="nl", currency="EUR"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys
    anthropic_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./competitor_monitor.db"

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""

    # Scraping
    proxy_urls: str = ""  # comma-separated
    playwright_headless: bool = True
    crawler_timeout_ms: int = 30_000
    crawler_max_retries: int = 3

    # Scheduling
    schedule_cron: str = "0 7 * * *"

    # Logging
    log_level: str = "INFO"

    @property
    def proxy_list(self) -> list[str]:
        return [p.strip() for p in self.proxy_urls.split(",") if p.strip()]


# ---------------------------------------------------------------------------
# Competitor definitions (Phase 1: 2 German competitors, configurable SKUs)
# Override at runtime by editing this list or loading from a YAML/DB later.
# ---------------------------------------------------------------------------
COMPETITORS: list[CompetitorConfig] = [
    CompetitorConfig(
        id="competitor_de_1",
        name="Competitor DE 1",
        market="DE",
        base_url="https://example-competitor-1.de",
        homepage_url="https://example-competitor-1.de",
        skus=[
            SKUConfig(
                id="sku_001",
                name="Example Product 1",
                url="https://example-competitor-1.de/products/example-1",
                price_alert_threshold_pct=5.0,
            ),
        ],
    ),
    CompetitorConfig(
        id="competitor_de_2",
        name="Competitor DE 2",
        market="DE",
        base_url="https://example-competitor-2.de",
        homepage_url="https://example-competitor-2.de",
        skus=[
            SKUConfig(
                id="sku_002",
                name="Example Product 2",
                url="https://example-competitor-2.de/products/example-2",
                price_alert_threshold_pct=5.0,
            ),
        ],
    ),
]

settings = Settings()
