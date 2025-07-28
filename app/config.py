import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    openai_api_key: str = ""
    alpha_vantage_key: str = ""
    news_api_key: str = ""
    
    # Database Configuration
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_use_ssl: bool = False
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Application Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Stock Lists
    stable_stocks: List[str] = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "SPY", "QQQ", "VTI", "VOO", "SCHD",
        "JNJ", "PG", "KO", "WMT", "HD",
        "JPM", "BAC", "BRK-B", "V", "MA"
    ]
    
    risky_stocks: List[str] = [
        "TSLA", "PLTR", "SNOW", "ZM", "UPST",
        "ROKU", "DKNG", "COIN", "TQQQ", "SOXL",
        "ARKK", "SPXL", "TECL", "RIVN", "META"
    ]
    
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


settings = Settings()