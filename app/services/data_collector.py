import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
import logging

from ..config import settings
from ..models.stock_data import (
    StockData, PriceData, TechnicalIndicators, 
    FundamentalData, SentimentData, StockCategory
)

logger = logging.getLogger(__name__)


class DataCollector:
    def __init__(self):
        self.av_key = settings.alpha_vantage_key
        self.news_api_key = settings.news_api_key
        if self.av_key:
            self.ts = TimeSeries(key=self.av_key, output_format='pandas')
            self.ti = TechIndicators(key=self.av_key, output_format='pandas')
    
    async def collect_stock_data(self, symbols: List[str]) -> Dict[str, StockData]:
        """Collect data for a list of stock symbols"""
        data = {}
        
        for symbol in symbols:
            try:
                logger.info(f"Collecting data for {symbol}")
                stock_data = await self._collect_single_stock(symbol)
                if stock_data:
                    data[symbol] = stock_data
                else:
                    logger.warning(f"No data collected for {symbol}")
            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {str(e)}")
                continue
        
        return data
    
    async def _collect_single_stock(self, symbol: str) -> Optional[StockData]:
        """Collect all data for a single stock"""
        try:
            # Get basic price data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            
            # Get recent price data
            hist = ticker.history(period="5d")
            if hist.empty:
                logger.warning(f"No historical data for {symbol}")
                return None
            
            # Get stock info
            info = ticker.info
            
            # Create price data
            price_data = self._create_price_data(hist, info)
            
            # Get technical indicators
            technical_indicators = await self._get_technical_indicators(symbol)
            
            # Get fundamental data
            fundamental_data = self._create_fundamental_data(info)
            
            # Get sentiment data
            sentiment_data = await self._get_sentiment_data(symbol)
            
            # Determine category
            category = self._determine_category(symbol)
            
            return StockData(
                symbol=symbol,
                date=datetime.now(),
                category=category,
                price_data=price_data,
                technical_indicators=technical_indicators,
                fundamental_data=fundamental_data,
                sentiment_data=sentiment_data
            )
            
        except Exception as e:
            logger.error(f"Error collecting data for {symbol}: {str(e)}")
            return None
    
    def _create_price_data(self, hist: pd.DataFrame, info: Dict) -> PriceData:
        """Create price data from historical data"""
        latest = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else None
        
        previous_close = previous['Close'] if previous is not None else latest['Close']
        change_percent = ((latest['Close'] - previous_close) / previous_close * 100) if previous_close > 0 else 0
        
        return PriceData(
            open=float(latest['Open']),
            high=float(latest['High']),
            low=float(latest['Low']),
            close=float(latest['Close']),
            volume=int(latest['Volume']),
            previous_close=float(previous_close),
            change_percent=float(change_percent)
        )
    
    async def _get_technical_indicators(self, symbol: str) -> Optional[TechnicalIndicators]:
        """Get technical indicators from Alpha Vantage"""
        if not self.av_key:
            logger.warning("Alpha Vantage API key not provided, skipping technical indicators")
            return None
        
        try:
            # Get RSI
            rsi_data, _ = self.ti.get_rsi(symbol=symbol, interval='daily', time_period=14, series_type='close')
            rsi = float(rsi_data.iloc[-1]) if not rsi_data.empty else None
            
            # Get MACD
            macd_data, _ = self.ti.get_macd(symbol=symbol, interval='daily', series_type='close')
            macd = float(macd_data['MACD'].iloc[-1]) if not macd_data.empty else None
            macd_signal = float(macd_data['MACD_Signal'].iloc[-1]) if not macd_data.empty else None
            
            # Get SMA indicators
            sma20_data, _ = self.ti.get_sma(symbol=symbol, interval='daily', time_period=20, series_type='close')
            sma_20 = float(sma20_data.iloc[-1]) if not sma20_data.empty else None
            
            sma50_data, _ = self.ti.get_sma(symbol=symbol, interval='daily', time_period=50, series_type='close')
            sma_50 = float(sma50_data.iloc[-1]) if not sma50_data.empty else None
            
            # Get Bollinger Bands
            bb_data, _ = self.ti.get_bbands(symbol=symbol, interval='daily', time_period=20, series_type='close')
            bollinger_upper = float(bb_data['Real Upper Band'].iloc[-1]) if not bb_data.empty else None
            bollinger_lower = float(bb_data['Real Lower Band'].iloc[-1]) if not bb_data.empty else None
            
            return TechnicalIndicators(
                rsi_14=rsi,
                macd=macd,
                macd_signal=macd_signal,
                sma_20=sma_20,
                sma_50=sma_50,
                bollinger_upper=bollinger_upper,
                bollinger_lower=bollinger_lower
            )
            
        except Exception as e:
            logger.error(f"Error getting technical indicators for {symbol}: {str(e)}")
            return None
    
    def _create_fundamental_data(self, info: Dict) -> FundamentalData:
        """Create fundamental data from stock info"""
        return FundamentalData(
            pe_ratio=info.get('forwardPE') or info.get('trailingPE'),
            market_cap=info.get('marketCap'),
            dividend_yield=info.get('dividendYield'),
            eps_ttm=info.get('trailingEps'),
            revenue_growth=info.get('revenueGrowth'),
            debt_to_equity=info.get('debtToEquity')
        )
    
    async def _get_sentiment_data(self, symbol: str) -> Optional[SentimentData]:
        """Get sentiment data from news sources"""
        if not self.news_api_key:
            logger.warning("News API key not provided, skipping sentiment data")
            return None
        
        try:
            # Search for news about the stock
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f"{symbol} stock",
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': settings.max_news_articles,
                'apiKey': self.news_api_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                news_data = response.json()
                articles_count = len(news_data.get('articles', []))
                
                # Simple sentiment scoring based on headline keywords
                sentiment_score = self._calculate_sentiment_score(news_data.get('articles', []))
                
                return SentimentData(
                    news_sentiment_score=sentiment_score,
                    news_articles_count=articles_count,
                    social_sentiment=0.5,  # Placeholder
                    analyst_rating="NEUTRAL"  # Placeholder
                )
            else:
                logger.warning(f"News API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting sentiment data for {symbol}: {str(e)}")
            return None
    
    def _calculate_sentiment_score(self, articles: List[Dict]) -> float:
        """Calculate simple sentiment score based on article headlines"""
        if not articles:
            return 0.5
        
        positive_words = ['up', 'rise', 'gain', 'bull', 'surge', 'jump', 'climb', 'rally', 'strong', 'beat']
        negative_words = ['down', 'fall', 'drop', 'bear', 'crash', 'plunge', 'decline', 'weak', 'miss', 'loss']
        
        total_score = 0
        for article in articles:
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            text = f"{title} {description}"
            
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            
            if positive_count + negative_count > 0:
                score = positive_count / (positive_count + negative_count)
            else:
                score = 0.5
            
            total_score += score
        
        return total_score / len(articles) if articles else 0.5
    
    def _determine_category(self, symbol: str) -> StockCategory:
        """Determine if stock is stable or risky based on configuration"""
        if symbol in settings.stable_stocks:
            return StockCategory.STABLE
        elif symbol in settings.risky_stocks:
            return StockCategory.RISKY
        else:
            # Default categorization logic
            return StockCategory.STABLE
    
    def get_watchlist(self) -> Dict[str, List[str]]:
        """Get the complete watchlist"""
        return {
            "stable": settings.stable_stocks,
            "risky": settings.risky_stocks
        }