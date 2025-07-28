import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    openai_api_key: str = ""
    alpha_vantage_key: str = ""
    news_api_key: str = ""
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Application Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Stock collection settings
    max_stable_stocks: int = 25
    max_risky_stocks: int = 15
    stock_validation_volume_threshold: int = 100000
    
    # Investment Amounts
    stable_investment: int = 200
    risky_investment: int = 50
    
    # Analysis Configuration
    analysis_timeout: int = 30  # seconds per stock
    max_news_articles: int = 10
    confidence_threshold: float = 0.6
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables (like old OpenSearch vars)


settings = Settings()