from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class StockCategory(str, Enum):
    STABLE = "STABLE"
    RISKY = "RISKY"


class TrendDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"


class Recommendation(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class PriceData(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: int
    previous_close: Optional[float] = None
    change_percent: Optional[float] = None


class TechnicalIndicators(BaseModel):
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    volume_sma: Optional[int] = None


class FundamentalData(BaseModel):
    pe_ratio: Optional[float] = None
    market_cap: Optional[int] = None
    dividend_yield: Optional[float] = None
    eps_ttm: Optional[float] = None
    revenue_growth: Optional[float] = None
    debt_to_equity: Optional[float] = None


class SentimentData(BaseModel):
    news_sentiment_score: Optional[float] = None
    news_articles_count: Optional[int] = None
    social_sentiment: Optional[float] = None
    analyst_rating: Optional[str] = None
    analyst_price_target: Optional[float] = None


class AIAnalysis(BaseModel):
    trend_direction: TrendDirection
    trend_strength: float = Field(ge=0, le=1)
    risk_score: float = Field(ge=0, le=1)
    recommendation: Recommendation
    confidence_level: float = Field(ge=0, le=1)
    target_allocation: StockCategory
    price_target_7d: Optional[float] = None
    price_target_30d: Optional[float] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    key_factors: List[str] = []
    reasoning: str


class StockData(BaseModel):
    symbol: str
    date: datetime
    category: StockCategory
    price_data: PriceData
    technical_indicators: Optional[TechnicalIndicators] = None
    fundamental_data: Optional[FundamentalData] = None
    sentiment_data: Optional[SentimentData] = None
    ai_analysis: Optional[AIAnalysis] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MarketOverview(BaseModel):
    date: datetime
    market_sentiment: str
    sp500_change: Optional[float] = None
    nasdaq_change: Optional[float] = None
    vix_level: Optional[float] = None
    market_themes: List[str] = []


class StockRecommendation(BaseModel):
    symbol: str
    allocation: int
    reasoning: str
    confidence: float = Field(ge=0, le=1)
    expected_return_30d: Optional[float] = None
    max_risk: Optional[float] = None