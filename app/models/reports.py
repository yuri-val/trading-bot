from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from .stock_data import MarketOverview, StockRecommendation


class DailyReport(BaseModel):
    report_id: str
    date: datetime
    report_type: str = "DAILY"
    market_overview: MarketOverview
    stable_recommendation: StockRecommendation
    risky_recommendation: StockRecommendation
    market_risks: List[str] = []
    analyzed_stocks_count: int
    processing_time_minutes: Optional[float] = None
    data_quality_score: Optional[float] = None
    content: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PerformanceMetrics(BaseModel):
    total_recommendations: int
    stable_picks_count: int
    risky_picks_count: int
    prediction_accuracy: Optional[float] = None
    avg_confidence_score: float


class TopPerformer(BaseModel):
    symbol: str
    frequency: int
    avg_return: Optional[float] = None


class SectorPerformance(BaseModel):
    technology: Optional[float] = None
    healthcare: Optional[float] = None
    financial: Optional[float] = None
    energy: Optional[float] = None
    consumer: Optional[float] = None


class MarketTrends(BaseModel):
    dominant_themes: List[str] = []
    sector_performance: SectorPerformance


class SummaryReport(BaseModel):
    report_id: str
    start_date: datetime
    end_date: datetime
    days_analyzed: int
    report_type: str = "SUMMARY_30D"
    performance_metrics: PerformanceMetrics
    top_stable_performers: List[TopPerformer] = []
    top_risky_performers: List[TopPerformer] = []
    market_trends: MarketTrends
    insights: List[str] = []
    next_month_outlook: str
    content: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReportRequest(BaseModel):
    start_date: Union[str, date]
    end_date: Union[str, date]
    format: str = "JSON"
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def parse_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return value


class CurrentRecommendations(BaseModel):
    date: datetime
    stable_recommendation: StockRecommendation
    risky_recommendation: StockRecommendation
    market_context: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }