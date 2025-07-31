import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from ..config import settings
from ..models.stock_data import (
    StockData, AIAnalysis, TrendDirection, Recommendation, StockCategory
)
from ..models.reports import StockRecommendation, MarketOverview
from .llm_adapter import llm_adapter

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    def __init__(self):
        self.llm_adapter = llm_adapter
        logger.info(f"LLM Analyzer initialized with providers: {self.llm_adapter.get_provider_status()}")

    async def analyze_stock_data(self, stock_data: StockData) -> Optional[AIAnalysis]:
        """Analyze stock data using LLM"""
        try:
            prompt = self._create_analysis_prompt(stock_data)

            response = await self.llm_adapter.chat_completion(
                prompt=prompt, 
                temperature=0.3, 
                max_tokens=1000,
                timeout=30
            )

            if response:
                analysis_data = self._parse_analysis_response(response)
                if analysis_data:
                    return AIAnalysis(**analysis_data)

            # Fallback analysis if LLM fails
            return self._fallback_analysis(stock_data)

        except Exception as e:
            logger.error(f"Error analyzing {stock_data.symbol}: {str(e)}")
            return self._fallback_analysis(stock_data)

    def _create_analysis_prompt(self, stock_data: StockData) -> str:
        """Create analysis prompt for LLM"""
        return f"""
You are an expert financial analyst. Analyze the following stock data for {stock_data.symbol}:

PRICE DATA:
- Current Price: ${stock_data.price_data.close:.2f}
- Daily Change: {stock_data.price_data.change_percent:.2f}%
- Volume: {stock_data.price_data.volume:,}
- High: ${stock_data.price_data.high:.2f}
- Low: ${stock_data.price_data.low:.2f}

TECHNICAL INDICATORS:
{self._format_technical_indicators(stock_data.technical_indicators)}

FUNDAMENTAL DATA:
{self._format_fundamental_data(stock_data.fundamental_data)}

SENTIMENT DATA:
{self._format_sentiment_data(stock_data.sentiment_data)}

CATEGORY: {stock_data.category.value}

Provide your analysis in the following JSON format:
{{
    "trend_direction": "BULLISH|BEARISH|SIDEWAYS",
    "trend_strength": 0.0-1.0,
    "risk_score": 0.0-1.0,
    "recommendation": "BUY|HOLD|SELL",
    "confidence_level": 0.0-1.0,
    "target_allocation": "STABLE|RISKY",
    "price_target_7d": number or null,
    "price_target_30d": number or null,
    "support_level": number or null,
    "resistance_level": number or null,
    "key_factors": ["factor1", "factor2", "factor3"],
    "reasoning": "Brief explanation of the analysis and recommendation"
}}

Consider:
1. Technical momentum and trend strength
2. Fundamental valuation metrics
3. Market sentiment and news flow
4. Risk-adjusted return potential
5. Stock category (stable vs risky) characteristics

Provide a conservative but actionable analysis.
"""

    def _format_technical_indicators(self, technical: Optional[object]) -> str:
        """Format technical indicators for prompt"""
        if not technical:
            return "- No technical indicators available"

        lines = []
        if hasattr(technical, 'rsi_14') and technical.rsi_14:
            lines.append(f"- RSI (14): {technical.rsi_14:.2f}")
        if hasattr(technical, 'macd') and technical.macd:
            lines.append(f"- MACD: {technical.macd:.4f}")
        if hasattr(technical, 'sma_20') and technical.sma_20:
            lines.append(f"- SMA 20: ${technical.sma_20:.2f}")
        if hasattr(technical, 'sma_50') and technical.sma_50:
            lines.append(f"- SMA 50: ${technical.sma_50:.2f}")
        if hasattr(technical, 'bollinger_upper') and technical.bollinger_upper:
            lines.append(f"- Bollinger Upper: ${technical.bollinger_upper:.2f}")
        if hasattr(technical, 'bollinger_lower') and technical.bollinger_lower:
            lines.append(f"- Bollinger Lower: ${technical.bollinger_lower:.2f}")

        return '\n'.join(lines) if lines else "- Limited technical data available"

    def _format_fundamental_data(self, fundamental: Optional[object]) -> str:
        """Format fundamental data for prompt"""
        if not fundamental:
            return "- No fundamental data available"

        lines = []
        if hasattr(fundamental, 'pe_ratio') and fundamental.pe_ratio:
            lines.append(f"- P/E Ratio: {fundamental.pe_ratio:.2f}")
        if hasattr(fundamental, 'market_cap') and fundamental.market_cap:
            market_cap_b = fundamental.market_cap / 1e9
            lines.append(f"- Market Cap: ${market_cap_b:.1f}B")
        if hasattr(fundamental, 'dividend_yield') and fundamental.dividend_yield is not None:
            lines.append(f"- Dividend Yield: {(fundamental.dividend_yield or 0)*100:.2f}%")
        if hasattr(fundamental, 'eps_ttm') and fundamental.eps_ttm:
            lines.append(f"- EPS (TTM): ${fundamental.eps_ttm:.2f}")
        if hasattr(fundamental, 'revenue_growth') and fundamental.revenue_growth is not None:
            lines.append(f"- Revenue Growth: {(fundamental.revenue_growth or 0)*100:.1f}%")

        return '\n'.join(lines) if lines else "- Limited fundamental data available"

    def _format_sentiment_data(self, sentiment: Optional[object]) -> str:
        """Format sentiment data for prompt"""
        if not sentiment:
            return "- No sentiment data available"

        lines = []
        if hasattr(sentiment, 'news_sentiment_score') and sentiment.news_sentiment_score is not None:
            lines.append(f"- News Sentiment: {sentiment.news_sentiment_score:.2f}")
        if hasattr(sentiment, 'news_articles_count') and sentiment.news_articles_count:
            lines.append(f"- News Articles: {sentiment.news_articles_count}")
        if hasattr(sentiment, 'analyst_rating') and sentiment.analyst_rating:
            lines.append(f"- Analyst Rating: {sentiment.analyst_rating}")

        return '\n'.join(lines) if lines else "- Limited sentiment data available"

    def _parse_analysis_response(self, response: str) -> Optional[Dict]:
        """Parse LLM response into structured data"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}')

            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                data = json.loads(json_str)

                # Validate and clean the data
                return self._validate_analysis_data(data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing analysis response: {str(e)}")

        return None

    def _validate_analysis_data(self, data: Dict) -> Dict:
        """Validate and clean analysis data"""
        validated = {}

        # Validate trend_direction
        trend = data.get('trend_direction', 'SIDEWAYS').upper()
        if trend in ['BULLISH', 'BEARISH', 'SIDEWAYS']:
            validated['trend_direction'] = trend
        else:
            validated['trend_direction'] = 'SIDEWAYS'

        # Validate numeric fields
        validated['trend_strength'] = max(0, min(1, data.get('trend_strength', 0.5)))
        validated['risk_score'] = max(0, min(1, data.get('risk_score', 0.5)))
        validated['confidence_level'] = max(0, min(1, data.get('confidence_level', 0.5)))

        # Validate recommendation
        rec = data.get('recommendation', 'HOLD').upper()
        if rec in ['BUY', 'HOLD', 'SELL']:
            validated['recommendation'] = rec
        else:
            validated['recommendation'] = 'HOLD'

        # Validate target_allocation
        allocation = data.get('target_allocation', 'STABLE').upper()
        if allocation in ['STABLE', 'RISKY']:
            validated['target_allocation'] = allocation
        else:
            validated['target_allocation'] = 'STABLE'

        # Optional numeric fields
        for field in ['price_target_7d', 'price_target_30d', 'support_level', 'resistance_level']:
            value = data.get(field)
            if value is not None and isinstance(value, (int, float)) and value > 0:
                validated[field] = float(value)
            else:
                validated[field] = None

        # Validate key_factors
        factors = data.get('key_factors', [])
        if isinstance(factors, list):
            validated['key_factors'] = [str(f) for f in factors[:5]]  # Limit to 5 factors
        else:
            validated['key_factors'] = []

        # Validate reasoning
        reasoning = data.get('reasoning', 'No specific reasoning provided.')
        validated['reasoning'] = str(reasoning)[:500]  # Limit length

        return validated

    def _fallback_analysis(self, stock_data: StockData) -> AIAnalysis:
        """Provide fallback analysis when LLM fails"""
        # Simple rule-based analysis
        change_percent = stock_data.price_data.change_percent or 0

        if change_percent > 2:
            trend = TrendDirection.BULLISH
            recommendation = Recommendation.BUY
        elif change_percent < -2:
            trend = TrendDirection.BEARISH
            recommendation = Recommendation.SELL
        else:
            trend = TrendDirection.SIDEWAYS
            recommendation = Recommendation.HOLD

        return AIAnalysis(
            trend_direction=trend,
            trend_strength=min(abs(change_percent) / 5, 1.0),
            risk_score=0.6 if stock_data.category == StockCategory.RISKY else 0.3,
            recommendation=recommendation,
            confidence_level=0.4,  # Low confidence for fallback
            target_allocation=stock_data.category,
            key_factors=["Fallback analysis", f"{change_percent:.1f}% daily change"],
            reasoning="Basic analysis due to LLM unavailability. Based on price movement only."
        )

    async def generate_daily_report(self, analyzed_stocks: List[StockData]) -> str:
        """Generate daily investment report"""
        try:
            # Filter and rank recommendations
            stable_picks = []
            risky_picks = []

            for stock in analyzed_stocks:
                if stock.ai_analysis and stock.ai_analysis.recommendation == Recommendation.BUY:
                    if stock.category == StockCategory.STABLE:
                        stable_picks.append(stock)
                    else:
                        risky_picks.append(stock)

            # Sort by confidence level
            stable_picks.sort(key=lambda x: x.ai_analysis.confidence_level, reverse=True)
            risky_picks.sort(key=lambda x: x.ai_analysis.confidence_level, reverse=True)

            # Create report prompt
            prompt = self._create_report_prompt(analyzed_stocks, stable_picks[:3], risky_picks[:3])

            response = await self.llm_adapter.chat_completion(
                prompt=prompt, 
                temperature=0.5, 
                max_tokens=2000,
                timeout=45
            )

            if response:
                return response
            else:
                return self._fallback_report(stable_picks, risky_picks)

        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
            return self._fallback_report(stable_picks if 'stable_picks' in locals() else [],
                                       risky_picks if 'risky_picks' in locals() else [])

    def _create_report_prompt(self, all_stocks: List[StockData],
                            stable_picks: List[StockData],
                            risky_picks: List[StockData]) -> str:
        """Create prompt for daily report generation"""
        return f"""
Create a daily investment report based on analysis of {len(all_stocks)} stocks.

TOP STABLE PICKS (for $200 investment):
{self._format_stock_picks(stable_picks)}

TOP RISKY PICKS (for $50 investment):
{self._format_stock_picks(risky_picks)}

Create a comprehensive daily report with the following structure:

1. **Market Overview**
   - Brief assessment of overall market conditions
   - Key market drivers and themes

2. **Stable Investment Recommendation ($200)**
   - Primary recommendation with specific reasoning
   - Entry strategy and key levels to watch
   - Risk factors to monitor

3. **Risky Investment Recommendation ($50)**
   - High-potential pick with growth rationale
   - Expected return potential and timeframe
   - Maximum risk tolerance

4. **Key Market Risks & Opportunities**
   - 3-4 major factors affecting the market
   - Sector rotation opportunities
   - Economic indicators to watch

5. **Technical & Fundamental Summary**
   - Market breadth and momentum
   - Valuation concerns or opportunities
   - Sentiment indicators

Keep the report actionable, concise, and focused on the specific $200/$50 allocation strategy.
Include specific price levels and timeframes where relevant.
"""

    def _format_stock_picks(self, picks: List[StockData]) -> str:
        """Format stock picks for report prompt"""
        if not picks:
            return "- No strong recommendations found"

        lines = []
        for stock in picks[:3]:
            if stock.ai_analysis:
                lines.append(f"- {stock.symbol}: ${stock.price_data.close:.2f} "
                           f"(Confidence: {stock.ai_analysis.confidence_level:.0%}, "
                           f"Target: ${stock.ai_analysis.price_target_30d:.2f} if available)")
                lines.append(f"  Reasoning: {stock.ai_analysis.reasoning[:100]}...")

        return '\n'.join(lines)

    def _fallback_report(self, stable_picks: List[StockData], risky_picks: List[StockData]) -> str:
        """Generate fallback report when LLM is unavailable"""
        stable_pick = stable_picks[0] if stable_picks else None
        risky_pick = risky_picks[0] if risky_picks else None

        report = f"""
# Daily Investment Report - {datetime.now().strftime('%Y-%m-%d')}

## Market Overview
Market analysis unavailable due to technical issues. Providing basic recommendations based on available data.

## Stable Investment Recommendation ($200)
"""

        if stable_pick:
            report += f"""
**Recommended:** {stable_pick.symbol} at ${stable_pick.price_data.close:.2f}
- Daily Change: {stable_pick.price_data.change_percent:.2f}%
- Category: Stable investment
- Basic analysis suggests {'positive' if stable_pick.price_data.change_percent > 0 else 'negative'} momentum
"""
        else:
            report += "No strong stable recommendations available today. Consider holding cash or index funds."

        report += "\n## Risky Investment Recommendation ($50)\n"

        if risky_pick:
            report += f"""
**Recommended:** {risky_pick.symbol} at ${risky_pick.price_data.close:.2f}
- Daily Change: {risky_pick.price_data.change_percent:.2f}%
- Category: High-risk/high-reward
- Volatile stock with potential for significant moves
"""
        else:
            report += "No strong risky recommendations available today. Consider waiting for better opportunities."

        report += """

## Important Notice
This is a simplified report due to technical limitations. Please conduct additional research before making investment decisions.

*Generated by automated system*
"""

        return report

    async def get_market_overview(self, analyzed_stocks: List[StockData]) -> MarketOverview:
        """Generate market overview from analyzed stocks"""
        try:
            # Calculate basic market metrics
            total_gains = sum(1 for stock in analyzed_stocks
                            if stock.price_data.change_percent and stock.price_data.change_percent > 0)
            total_stocks = len(analyzed_stocks)
            market_sentiment = "POSITIVE" if total_gains > total_stocks * 0.6 else "NEGATIVE" if total_gains < total_stocks * 0.4 else "MIXED"

            # Get key themes from stock analysis
            themes = []
            for stock in analyzed_stocks:
                if stock.ai_analysis and stock.ai_analysis.key_factors:
                    themes.extend(stock.ai_analysis.key_factors)

            # Get most common themes
            from collections import Counter
            common_themes = [theme for theme, count in Counter(themes).most_common(3)]

            return MarketOverview(
                date=datetime.now(),
                market_sentiment=market_sentiment,
                market_themes=common_themes or ["Data analysis", "Technical indicators", "Market volatility"]
            )

        except Exception as e:
            logger.error(f"Error creating market overview: {str(e)}")
            return MarketOverview(
                date=datetime.now(),
                market_sentiment="MIXED",
                market_themes=["Market analysis", "Technical indicators", "Investment opportunities"]
            )
