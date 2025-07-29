import yfinance as yf
import requests
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
import requests
import logging

from ..config import settings
from ..models.stock_data import (
    StockData, PriceData, TechnicalIndicators, 
    FundamentalData, SentimentData, StockCategory
)
from .stock_list_collector import StockListCollector
from .json_storage import JSONStorage

logger = logging.getLogger(__name__)


class DataCollector:
    def __init__(self):
        self.av_key = settings.alpha_vantage_key
        self.news_api_key = settings.news_api_key
        self.twelve_data_key = settings.twelve_data_api_key
        self.iex_token = settings.iex_token
        self.fmp_api_key = settings.fmp_api_key
        self.stock_collector = StockListCollector()
        self.storage = JSONStorage()
        if self.av_key:
            self.ts = TimeSeries(key=self.av_key, output_format='pandas')
            self.ti = TechIndicators(key=self.av_key, output_format='pandas')
        
        # Financial Modeling Prep base URL
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"
    
    async def collect_daily_data(self) -> Dict[str, StockData]:
        """Collect data for all stocks in the watchlist"""
        # Update stock lists first
        stock_lists = await self.stock_collector.update_stock_lists()
        all_symbols = stock_lists["stable"] + stock_lists["risky"]
        
        logger.info(f"Collecting data for {len(all_symbols)} stocks")
        
        data = {}
        for i, symbol in enumerate(all_symbols):
            try:
                logger.info(f"Collecting data for {symbol}")
                stock_data = await self._collect_single_stock(symbol, stock_lists)
                if stock_data:
                    # Save to storage immediately
                    await self.storage.save_stock_data(stock_data)
                    data[symbol] = stock_data
                else:
                    logger.warning(f"No data collected for {symbol}")
                
                # Rate limiting: Financial Modeling Prep allows 250 calls/day for free
                # Add 2 second delay to be conservative
                if i < len(all_symbols) - 1:  # Don't delay after last stock
                    logger.info(f"Rate limiting: waiting 2 seconds before next stock...")
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {str(e)}")
                continue
        
        # Save updated stock lists
        await self.stock_collector.save_lists_to_file()
        
        return data
    
    async def collect_stock_data(self, symbols: List[str]) -> Dict[str, StockData]:
        """Collect data for a specific list of stock symbols"""
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
    
    async def _collect_single_stock(self, symbol: str, stock_lists: Optional[Dict] = None) -> Optional[StockData]:
        """Collect all data for a single stock"""
        try:
            # Get basic price data from Financial Modeling Prep
            price_data = await self._get_fmp_price_data(symbol)
            if not price_data:
                logger.warning(f"No price data for {symbol}")
                return None
            
            # Get technical indicators
            technical_indicators = await self._get_technical_indicators(symbol)
            
            # Get fundamental data from Financial Modeling Prep
            fundamental_data = await self._get_fmp_fundamental_data(symbol)
            
            # Get sentiment data
            sentiment_data = await self._get_sentiment_data(symbol)
            
            # Determine category
            category = self._determine_category(symbol, stock_lists)
            
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
    
    async def _get_fmp_price_data(self, symbol: str) -> Optional[PriceData]:
        """Get price data from Financial Modeling Prep API"""
        if not self.fmp_api_key:
            logger.warning("Financial Modeling Prep API key not provided")
            return None
        
        try:
            # Get real-time quote data
            url = f"{self.fmp_base_url}/quote/{symbol}"
            params = {"apikey": self.fmp_api_key}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or len(data) == 0:
                logger.warning(f"No quote data found for {symbol}")
                return None
            
            quote = data[0]  # FMP returns array with single quote
            
            # Extract price data
            current_close = float(quote.get('price', 0))
            previous_close = float(quote.get('previousClose', current_close))
            
            # Calculate change percent
            change = float(quote.get('change', 0))
            change_percent = float(quote.get('changesPercentage', 0))
            
            return PriceData(
                open=float(quote.get('open', current_close)),
                high=float(quote.get('dayHigh', current_close)),
                low=float(quote.get('dayLow', current_close)),
                close=current_close,
                volume=int(quote.get('volume', 0)),
                previous_close=previous_close,
                change_percent=change_percent
            )
            
        except Exception as e:
            logger.error(f"Failed to get Financial Modeling Prep price data for {symbol}: {str(e)}")
            return None
    
    async def _get_fmp_fundamental_data(self, symbol: str) -> Optional[FundamentalData]:
        """Get fundamental data from Financial Modeling Prep API"""
        if not self.fmp_api_key:
            return None
        
        try:
            # Get key metrics from Financial Modeling Prep
            url = f"{self.fmp_base_url}/key-metrics/{symbol}"
            params = {"apikey": self.fmp_api_key, "limit": 1}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or len(data) == 0:
                # Return basic structure if no data available
                return FundamentalData(
                    market_cap=None,
                    pe_ratio=None,
                    dividend_yield=None,
                    eps=None,
                    revenue_growth=None,
                    debt_to_equity=None,
                    price_to_book=None,
                    roe=None
                )
            
            metrics = data[0]  # Most recent year data
            
            return FundamentalData(
                market_cap=metrics.get('marketCap'),
                pe_ratio=metrics.get('peRatio'),
                dividend_yield=metrics.get('dividendYield'),
                eps=metrics.get('netIncomePerShare'),
                revenue_growth=metrics.get('revenuePerShare'),
                debt_to_equity=metrics.get('debtToEquity'),
                price_to_book=metrics.get('priceToBookRatio'),
                roe=metrics.get('returnOnEquity')
            )
            
        except Exception as e:
            logger.error(f"Failed to get Financial Modeling Prep fundamental data for {symbol}: {str(e)}")
            # Return basic structure on error
            return FundamentalData(
                market_cap=None,
                pe_ratio=None,
                dividend_yield=None,
                eps=None,
                revenue_growth=None,
                debt_to_equity=None,
                price_to_book=None,
                roe=None
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
    
    def _determine_category(self, symbol: str, stock_lists: Optional[Dict] = None) -> StockCategory:
        """Determine if stock is stable or risky based on dynamic lists"""
        if stock_lists:
            if symbol in stock_lists.get("stable", []):
                return StockCategory.STABLE
            elif symbol in stock_lists.get("risky", []):
                return StockCategory.RISKY
        
        # Fallback: try to get current lists from collector
        current_lists = self.stock_collector.get_current_lists()
        if symbol in current_lists.get("stable", []):
            return StockCategory.STABLE
        elif symbol in current_lists.get("risky", []):
            return StockCategory.RISKY
        
        # Default to stable for unknown stocks
        return StockCategory.STABLE
    
    async def get_watchlist(self) -> Dict[str, List[str]]:
        """Get the complete watchlist from dynamic stock collector"""
        current_lists = self.stock_collector.get_current_lists()
        
        # If lists are empty, try to load from file or update
        if not current_lists["stable"] and not current_lists["risky"]:
            # Try loading from file first
            loaded = await self.stock_collector.load_lists_from_file()
            if loaded:
                # Get the updated lists after loading from file
                current_lists = self.stock_collector.get_current_lists()
            else:
                # If no saved file, update from internet
                current_lists = await self.stock_collector.update_stock_lists()
        
        return {
            "stable": current_lists["stable"],
            "risky": current_lists["risky"],
            "last_updated": current_lists.get("last_updated")
        }