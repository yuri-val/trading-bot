import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import requests

from ..config import settings
from ..models.reports import AIInvestmentRecommendation, TopPerformer, SummaryReport
from ..models.stock_data import StockData, StockCategory
from .analyzer import LLMAnalyzer
from .data_collector import DataCollector
from .json_storage import JSONStorage

logger = logging.getLogger(__name__)


class AIInvestmentAdvisor:
    def __init__(self):
        self.analyzer = LLMAnalyzer()
        self.data_collector = DataCollector()
        self.storage = JSONStorage()
        self.news_api_key = settings.news_api_key
    
    async def generate_investment_recommendations(
        self, 
        summary_report: SummaryReport
    ) -> Tuple[Optional[AIInvestmentRecommendation], Optional[AIInvestmentRecommendation]]:
        """Generate AI-powered investment recommendations from summary report"""
        try:
            logger.info("Generating AI investment recommendations from summary report")
            
            # Get current market data for top performers
            stable_candidates = await self._analyze_candidates(
                summary_report.top_stable_performers, 
                StockCategory.STABLE
            )
            risky_candidates = await self._analyze_candidates(
                summary_report.top_risky_performers, 
                StockCategory.RISKY
            )
            
            # Generate AI recommendations for each category
            stable_rec = await self._generate_single_recommendation(
                stable_candidates, StockCategory.STABLE, summary_report
            )
            risky_rec = await self._generate_single_recommendation(
                risky_candidates, StockCategory.RISKY, summary_report
            )
            
            return stable_rec, risky_rec
            
        except Exception as e:
            logger.error(f"Error generating AI investment recommendations: {str(e)}")
            return None, None
    
    async def _analyze_candidates(
        self, 
        performers: List[TopPerformer], 
        category: StockCategory
    ) -> List[Dict]:
        """Analyze candidate stocks with current market data"""
        candidates = []
        
        for performer in performers[:5]:  # Analyze top 5 candidates
            try:
                # Get current stock data
                stock_data = await self._get_current_stock_data(performer.symbol)
                if not stock_data:
                    continue
                
                # Get recent news sentiment
                news_data = await self._get_recent_news(performer.symbol)
                
                # Get additional market metrics
                market_metrics = await self._get_market_metrics(performer.symbol)
                
                candidates.append({
                    'symbol': performer.symbol,
                    'frequency': performer.frequency,
                    'stock_data': stock_data,
                    'news_data': news_data,
                    'market_metrics': market_metrics
                })
                
            except Exception as e:
                logger.error(f"Error analyzing candidate {performer.symbol}: {str(e)}")
                continue
        
        return candidates
    
    async def _get_current_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get current stock data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="5d")
            
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change_pct = (current_price - prev_close) / prev_close * 100
            
            return {
                'current_price': float(current_price),
                'change_percent': float(change_pct),
                'volume': int(hist['Volume'].iloc[-1]),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'eps': info.get('trailingEps'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow'),
                'recommendation': info.get('recommendationKey'),
                'target_price': info.get('targetMeanPrice')
            }
        except Exception as e:
            logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            return None
    
    async def _get_recent_news(self, symbol: str) -> Optional[Dict]:
        """Get recent news and sentiment for stock"""
        if not self.news_api_key:
            return None
        
        try:
            # Get news from last 7 days
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f"{symbol} stock OR earnings OR financial",
                'language': 'en',
                'from': from_date,
                'sortBy': 'publishedAt',
                'pageSize': 10,
                'apiKey': self.news_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            articles = data.get('articles', [])
            
            # Calculate sentiment score
            sentiment_score = self._calculate_news_sentiment(articles)
            
            return {
                'articles_count': len(articles),
                'sentiment_score': sentiment_score,
                'latest_headlines': [article['title'] for article in articles[:3]]
            }
            
        except Exception as e:
            logger.error(f"Error getting news for {symbol}: {str(e)}")
            return None
    
    def _calculate_news_sentiment(self, articles: List[Dict]) -> float:
        """Calculate news sentiment score (0-1)"""
        if not articles:
            return 0.5
        
        positive_words = [
            'beat', 'exceeds', 'strong', 'growth', 'profit', 'gain', 'rise', 'up', 
            'bull', 'surge', 'rally', 'outperform', 'upgrade', 'buy', 'positive'
        ]
        negative_words = [
            'miss', 'disappoints', 'weak', 'decline', 'loss', 'fall', 'down', 
            'bear', 'crash', 'drop', 'underperform', 'downgrade', 'sell', 'negative'
        ]
        
        total_score = 0
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}'.lower()"
            
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            
            if positive_count + negative_count > 0:
                score = positive_count / (positive_count + negative_count)
            else:
                score = 0.5
            
            total_score += score
        
        return total_score / len(articles)
    
    async def _get_market_metrics(self, symbol: str) -> Dict:
        """Get additional market metrics"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get analyst recommendations
            recommendations = ticker.recommendations
            upgrades_downgrades = ticker.upgrades_downgrades
            
            metrics = {
                'analyst_recommendations': None,
                'recent_upgrades_downgrades': None
            }
            
            if recommendations is not None and not recommendations.empty:
                latest_rec = recommendations.tail(1)
                if not latest_rec.empty:
                    metrics['analyst_recommendations'] = {
                        'strongBuy': int(latest_rec['strongBuy'].iloc[-1]) if 'strongBuy' in latest_rec.columns else 0,
                        'buy': int(latest_rec['buy'].iloc[-1]) if 'buy' in latest_rec.columns else 0,
                        'hold': int(latest_rec['hold'].iloc[-1]) if 'hold' in latest_rec.columns else 0,
                        'sell': int(latest_rec['sell'].iloc[-1]) if 'sell' in latest_rec.columns else 0,
                        'strongSell': int(latest_rec['strongSell'].iloc[-1]) if 'strongSell' in latest_rec.columns else 0
                    }
            
            if upgrades_downgrades is not None and not upgrades_downgrades.empty:
                recent_changes = upgrades_downgrades.tail(3)
                metrics['recent_upgrades_downgrades'] = recent_changes.to_dict('records')
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting market metrics for {symbol}: {str(e)}")
            return {}
    
    async def _generate_single_recommendation(
        self, 
        candidates: List[Dict], 
        category: StockCategory,
        summary_report: SummaryReport
    ) -> Optional[AIInvestmentRecommendation]:
        """Generate single investment recommendation using AI analysis"""
        if not candidates:
            return None
        
        try:
            allocation = settings.stable_investment if category == StockCategory.STABLE else settings.risky_investment
            category_name = "stable" if category == StockCategory.STABLE else "risky"
            
            # Create comprehensive analysis prompt
            prompt = self._create_analysis_prompt(candidates, summary_report, category_name, allocation)
            
            # Get AI analysis
            response = await self.analyzer._call_openai(prompt, temperature=0.3)
            
            if response:
                # Parse AI response
                recommendation = await self._parse_ai_response(response, category, allocation)
                return recommendation
            else:
                # Fallback to best candidate by frequency
                return self._create_fallback_recommendation(candidates, category, allocation)
                
        except Exception as e:
            logger.error(f"Error generating {category_name} recommendation: {str(e)}")
            return self._create_fallback_recommendation(candidates, category, allocation)
    
    def _create_analysis_prompt(
        self, 
        candidates: List[Dict], 
        summary_report: SummaryReport, 
        category_name: str, 
        allocation: int
    ) -> str:
        """Create comprehensive analysis prompt for AI"""
        
        candidates_data = []
        for candidate in candidates:
            stock_data = candidate['stock_data']
            news_data = candidate['news_data']
            market_metrics = candidate['market_metrics']
            
            candidate_info = f"""
Stock: {candidate['symbol']}
- Frequency in reports: {candidate['frequency']} times
- Current price: ${stock_data.get('current_price', 'N/A'):.2f}
- Daily change: {stock_data.get('change_percent', 0):.2f}%
- Market cap: ${stock_data.get('market_cap', 0):,}
- P/E ratio: {stock_data.get('pe_ratio', 'N/A')}
- Dividend yield: {stock_data.get('dividend_yield', 0)*100:.2f}% if stock_data.get('dividend_yield') else 'N/A'
- Beta: {stock_data.get('beta', 'N/A')}
- 52-week range: ${stock_data.get('52_week_low', 0):.2f} - ${stock_data.get('52_week_high', 0):.2f}
- Analyst target: ${stock_data.get('target_price', 'N/A')}
- News sentiment (last 7 days): {news_data.get('sentiment_score', 0.5)*100:.0f}%
- Recent news articles: {news_data.get('articles_count', 0)}
"""
            
            if news_data and news_data.get('latest_headlines'):
                candidate_info += f"- Latest headlines: {'; '.join(news_data['latest_headlines'][:2])}\n"
            
            if market_metrics and market_metrics.get('analyst_recommendations'):
                recs = market_metrics['analyst_recommendations']
                total_recs = sum(recs.values())
                if total_recs > 0:
                    candidate_info += f"- Analyst ratings: {recs.get('strongBuy', 0)} Strong Buy, {recs.get('buy', 0)} Buy, {recs.get('hold', 0)} Hold\n"
            
            candidates_data.append(candidate_info)
        
        prompt = f"""
You are an investment expert. Analyze the following 30-day stock report and provide an investment recommendation.

## Period Summary:
- Analysis period: {summary_report.days_analyzed} days
- Total recommendations: {summary_report.performance_metrics.total_recommendations}
- Average confidence level: {summary_report.performance_metrics.avg_confidence_score:.1%}
- Market trends: {', '.join(summary_report.market_trends.dominant_themes[:3])}

## Candidates for {category_name} investment (${allocation}):

{''.join(candidates_data)}

## Task:
Select ONE best stock for ${allocation} investment and provide detailed analysis.

## Analysis Criteria:
1. **Fundamental metrics**: P/E ratio, market capitalization, dividend yield
2. **Technical analysis**: current position relative to 52-week range
3. **News background**: sentiment and recent events
4. **Analyst recommendations**: professional opinions
5. **Report frequency**: system recommendation stability
6. **Risk profile**: alignment with {category_name} category

## Response Format (JSON):
{{
  "symbol": "TICKER",
  "reasoning": "Detailed justification with analysis of all factors (3-4 sentences)",
  "confidence": 0.85,
  "target_price": 150.00,
  "expected_return": 0.12,
  "risk_factors": ["factor 1", "factor 2"],
  "news_sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
  "key_metrics": {{
    "pe_ratio": 25.5,
    "market_cap": 1000000000,
    "beta": 1.2
  }}
}}

Response must be in JSON format only, without additional text.
"""
        
        return prompt
    
    async def _parse_ai_response(
        self, 
        response: str, 
        category: StockCategory, 
        allocation: int
    ) -> Optional[AIInvestmentRecommendation]:
        """Parse AI response and create recommendation"""
        try:
            # Clean response and extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            data = json.loads(response.strip())
            
            return AIInvestmentRecommendation(
                symbol=data['symbol'],
                category=category.value,
                allocation=allocation,
                confidence=float(data.get('confidence', 0.7)),
                reasoning=data.get('reasoning', 'AI-generated recommendation'),
                current_price=None,  # Will be filled later
                target_price=float(data.get('target_price')) if data.get('target_price') else None,
                expected_return=float(data.get('expected_return')) if data.get('expected_return') else None,
                risk_factors=data.get('risk_factors', []),
                news_sentiment=data.get('news_sentiment', 'NEUTRAL'),
                key_metrics=data.get('key_metrics', {})
            )
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return None
    
    def _create_fallback_recommendation(
        self, 
        candidates: List[Dict], 
        category: StockCategory, 
        allocation: int
    ) -> AIInvestmentRecommendation:
        """Create fallback recommendation when AI analysis fails"""
        # Choose candidate with highest frequency
        best_candidate = max(candidates, key=lambda x: x['frequency'])
        
        stock_data = best_candidate['stock_data']
        news_data = best_candidate['news_data'] or {}
        
        return AIInvestmentRecommendation(
            symbol=best_candidate['symbol'],
            category=category.value,
            allocation=allocation,
            confidence=0.6,
            reasoning=f"Selected {best_candidate['symbol']} as most frequently recommended stock in {category.value.lower()} category with {best_candidate['frequency']} recommendations during analysis period.",
            current_price=stock_data.get('current_price'),
            target_price=stock_data.get('target_price'),
            expected_return=0.08 if category == StockCategory.STABLE else 0.15,
            risk_factors=["Market volatility", "Sector-specific risks"],
            news_sentiment=self._sentiment_to_text(news_data.get('sentiment_score', 0.5)),
            key_metrics={
                'pe_ratio': stock_data.get('pe_ratio'),
                'market_cap': stock_data.get('market_cap'),
                'beta': stock_data.get('beta')
            }
        )
    
    def _sentiment_to_text(self, score: float) -> str:
        """Convert sentiment score to text"""
        if score > 0.6:
            return "POSITIVE"
        elif score < 0.4:
            return "NEGATIVE"
        else:
            return "NEUTRAL"