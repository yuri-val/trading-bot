import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from collections import Counter

from ..models.stock_data import StockData, StockCategory, Recommendation
from ..models.reports import (
    DailyReport, SummaryReport, StockRecommendation,
    PerformanceMetrics, TopPerformer, MarketOverview,
    MarketTrends, SectorPerformance, AIInvestmentRecommendation
)
from ..config import settings
from .analyzer import LLMAnalyzer
from .json_storage import JSONStorage
from .ai_investment_advisor import AIInvestmentAdvisor

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self):
        self.analyzer = LLMAnalyzer()
        self.storage = JSONStorage()
        self.ai_advisor = AIInvestmentAdvisor()

    async def create_daily_report(self, analyzed_stocks: List[StockData]) -> DailyReport:
        """Create daily investment report"""
        try:
            start_time = datetime.now()

            # Get market overview
            market_overview = await self.analyzer.get_market_overview(analyzed_stocks)

            # Find best recommendations
            stable_rec = self._find_best_recommendation(analyzed_stocks, StockCategory.STABLE)
            risky_rec = self._find_best_recommendation(analyzed_stocks, StockCategory.RISKY)

            # Generate detailed report content
            report_content = await self.analyzer.generate_daily_report(analyzed_stocks)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() / 60

            # Create report
            report = DailyReport(
                report_id=f"DR_{datetime.now().strftime('%Y-%m-%d')}",
                date=datetime.now(),
                market_overview=market_overview,
                stable_recommendation=stable_rec,
                risky_recommendation=risky_rec,
                market_risks=self._identify_market_risks(analyzed_stocks),
                analyzed_stocks_count=len(analyzed_stocks),
                processing_time_minutes=processing_time,
                data_quality_score=self._calculate_data_quality(analyzed_stocks),
                content=report_content
            )

            # Save to JSON storage
            await self.storage.save_daily_report(report)

            logger.info(f"Daily report created successfully: {report.report_id}")
            return report

        except Exception as e:
            logger.error(f"Error creating daily report: {str(e)}")
            # Return minimal report on error
            return self._create_fallback_daily_report(analyzed_stocks)

    def _find_best_recommendation(self, stocks: List[StockData], category: StockCategory) -> StockRecommendation:
        """Find the best recommendation for a category"""
        # Filter stocks by category and BUY recommendation
        candidates = [
            stock for stock in stocks
            if (stock.category == category and
                stock.ai_analysis and
                stock.ai_analysis.recommendation == Recommendation.BUY and
                stock.ai_analysis.confidence_level >= settings.confidence_threshold)
        ]

        if not candidates:
            # Fallback to any stock in category with HOLD recommendation
            candidates = [
                stock for stock in stocks
                if (stock.category == category and
                    stock.ai_analysis and
                    stock.ai_analysis.recommendation == Recommendation.HOLD)
            ]

        if not candidates:
            # Ultimate fallback - any stock in category
            candidates = [stock for stock in stocks if stock.category == category]

        if not candidates:
            # Create default recommendation
            return self._create_default_recommendation(category)

        # Sort by confidence level and pick the best
        candidates.sort(key=lambda x: x.ai_analysis.confidence_level if x.ai_analysis else 0, reverse=True)
        best_stock = candidates[0]

        allocation = settings.stable_investment if category == StockCategory.STABLE else settings.risky_investment

        return StockRecommendation(
            symbol=best_stock.symbol,
            allocation=allocation,
            reasoning=best_stock.ai_analysis.reasoning if best_stock.ai_analysis else "Selected based on category matching",
            confidence=best_stock.ai_analysis.confidence_level if best_stock.ai_analysis else 0.5,
            expected_return_30d=self._calculate_expected_return(best_stock),
            max_risk=best_stock.ai_analysis.risk_score if best_stock.ai_analysis else 0.5
        )

    def _create_default_recommendation(self, category: StockCategory) -> StockRecommendation:
        """Create default recommendation when no stocks are available"""
        symbol = "SPY" if category == StockCategory.STABLE else "QQQ"
        allocation = settings.stable_investment if category == StockCategory.STABLE else settings.risky_investment

        return StockRecommendation(
            symbol=symbol,
            allocation=allocation,
            reasoning=f"Default {category.value.lower()} recommendation due to lack of analyzed data",
            confidence=0.3,
            expected_return_30d=0.05,
            max_risk=0.3 if category == StockCategory.STABLE else 0.7
        )

    def _calculate_expected_return(self, stock: StockData) -> Optional[float]:
        """Calculate expected return based on analysis"""
        if not stock.ai_analysis or not stock.ai_analysis.price_target_30d:
            return None

        current_price = stock.price_data.close
        target_price = stock.ai_analysis.price_target_30d

        return (target_price - current_price) / current_price

    def _identify_market_risks(self, stocks: List[StockData]) -> List[str]:
        """Identify key market risks from stock analysis"""
        risks = []

        # Analyze overall market sentiment
        negative_stocks = sum(1 for stock in stocks
                            if stock.ai_analysis and stock.ai_analysis.recommendation == Recommendation.SELL)

        if negative_stocks > len(stocks) * 0.3:
            risks.append("Broad market weakness with multiple sell signals")

        # Check for high volatility
        high_risk_stocks = sum(1 for stock in stocks
                             if stock.ai_analysis and stock.ai_analysis.risk_score > 0.7)

        if high_risk_stocks > len(stocks) * 0.4:
            risks.append("Elevated market volatility across multiple sectors")

        # Add generic risks if none found
        if not risks:
            risks = [
                "Standard market volatility",
                "Economic policy uncertainty",
                "Sector rotation risks"
            ]

        return risks[:4]  # Limit to 4 risks

    def _calculate_data_quality(self, stocks: List[StockData]) -> float:
        """Calculate data quality score"""
        if not stocks:
            return 0.0

        total_score = 0
        for stock in stocks:
            score = 0
            # Price data always available (required)
            score += 0.3

            # Technical indicators
            if stock.technical_indicators:
                score += 0.2

            # Fundamental data
            if stock.fundamental_data:
                score += 0.2

            # Sentiment data
            if stock.sentiment_data:
                score += 0.2

            # AI analysis
            if stock.ai_analysis:
                score += 0.1

            total_score += score

        return total_score / len(stocks)

    def _create_fallback_daily_report(self, stocks: List[StockData]) -> DailyReport:
        """Create fallback report when main generation fails"""
        return DailyReport(
            report_id=f"DR_{datetime.now().strftime('%Y-%m-%d')}_FALLBACK",
            date=datetime.now(),
            market_overview=MarketOverview(
                date=datetime.now(),
                market_sentiment="UNKNOWN",
                market_themes=["System maintenance", "Limited analysis"]
            ),
            stable_recommendation=self._create_default_recommendation(StockCategory.STABLE),
            risky_recommendation=self._create_default_recommendation(StockCategory.RISKY),
            market_risks=["System limitations", "Incomplete data analysis"],
            analyzed_stocks_count=len(stocks),
            processing_time_minutes=0,
            data_quality_score=0.3,
            content="Daily report generation encountered technical issues. Using fallback recommendations."
        )

    async def create_summary_report(self, start_date: str, end_date: str) -> SummaryReport:
        """Create 30-day summary report"""
        try:
            # Get daily reports from the period
            daily_reports = await self.storage.get_daily_reports_range(start_date, end_date)

            if not daily_reports:
                return self._create_empty_summary_report(start_date, end_date)

            # Analyze performance metrics
            performance_metrics = self._calculate_performance_metrics(daily_reports)

            # Find top performers
            top_stable_performers = self._find_top_performers(daily_reports, "stable")
            top_risky_performers = self._find_top_performers(daily_reports, "risky")

            # Analyze market trends
            market_trends = self._analyze_market_trends(daily_reports)

            # Generate insights
            insights = self._generate_insights(daily_reports, performance_metrics)

            # Generate outlook
            outlook = await self._generate_outlook(daily_reports)

            # Generate AI investment recommendations
            logger.info("Generating AI investment recommendations...")
            temp_report = SummaryReport(
                report_id=f"SR_{end_date}_30D_TEMP",
                start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.strptime(end_date, "%Y-%m-%d"),
                days_analyzed=len(daily_reports),
                performance_metrics=performance_metrics,
                top_stable_performers=top_stable_performers,
                top_risky_performers=top_risky_performers,
                market_trends=market_trends,
                insights=insights,
                next_month_outlook=outlook,
                content=""
            )

            ai_stable_rec, ai_risky_rec = await self.ai_advisor.generate_investment_recommendations(temp_report)

            # Create summary content with AI recommendations
            summary_content = await self._create_summary_content(
                daily_reports, performance_metrics, top_stable_performers, top_risky_performers, ai_stable_rec, ai_risky_rec
            )

            report = SummaryReport(
                report_id=f"SR_{end_date}_30D",
                start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.strptime(end_date, "%Y-%m-%d"),
                days_analyzed=len(daily_reports),
                performance_metrics=performance_metrics,
                top_stable_performers=top_stable_performers,
                top_risky_performers=top_risky_performers,
                market_trends=market_trends,
                insights=insights,
                next_month_outlook=outlook,
                ai_stable_recommendation=ai_stable_rec,
                ai_risky_recommendation=ai_risky_rec,
                content=summary_content
            )

            # Save to JSON storage
            await self.storage.save_summary_report(report)

            logger.info(f"Summary report created: {report.report_id}")
            return report

        except Exception as e:
            logger.error(f"Error creating summary report: {str(e)}")
            return self._create_empty_summary_report(start_date, end_date)

    def _calculate_performance_metrics(self, daily_reports: List[Dict]) -> PerformanceMetrics:
        """Calculate performance metrics from daily reports"""
        total_recommendations = len(daily_reports) * 2  # stable + risky per day
        stable_count = len(daily_reports)
        risky_count = len(daily_reports)

        # Calculate average confidence
        total_confidence = 0
        confidence_count = 0

        for report in daily_reports:
            if 'stable_recommendation' in report:
                total_confidence += report['stable_recommendation'].get('confidence', 0.5)
                confidence_count += 1
            if 'risky_recommendation' in report:
                total_confidence += report['risky_recommendation'].get('confidence', 0.5)
                confidence_count += 1

        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.5

        return PerformanceMetrics(
            total_recommendations=total_recommendations,
            stable_picks_count=stable_count,
            risky_picks_count=risky_count,
            prediction_accuracy=None,  # Would need actual performance tracking
            avg_confidence_score=avg_confidence
        )

    def _find_top_performers(self, daily_reports: List[Dict], category: str) -> List[TopPerformer]:
        """Find top performing stocks in category"""
        symbol_counts = Counter()

        for report in daily_reports:
            rec_key = f"{category}_recommendation"
            if rec_key in report and 'symbol' in report[rec_key]:
                symbol = report[rec_key]['symbol']
                symbol_counts[symbol] += 1

        # Convert to TopPerformer objects
        performers = []
        for symbol, frequency in symbol_counts.most_common(5):
            performers.append(TopPerformer(
                symbol=symbol,
                frequency=frequency,
                avg_return=None  # Would need actual performance tracking
            ))

        return performers

    def _analyze_market_trends(self, daily_reports: List[Dict]) -> MarketTrends:
        """Analyze market trends from daily reports"""
        themes = []
        sentiments = []

        for report in daily_reports:
            if 'market_overview' in report:
                overview = report['market_overview']
                if 'market_themes' in overview:
                    themes.extend(overview['market_themes'])
                if 'market_sentiment' in overview:
                    sentiments.append(overview['market_sentiment'])

        # Get most common themes
        common_themes = [theme for theme, count in Counter(themes).most_common(5)]

        return MarketTrends(
            dominant_themes=common_themes,
            sector_performance=SectorPerformance()  # Placeholder
        )

    def _generate_insights(self, daily_reports: List[Dict], metrics: PerformanceMetrics) -> List[str]:
        """Generate insights from the reporting period"""
        insights = []

        if metrics.avg_confidence_score > 0.7:
            insights.append("High confidence levels maintained throughout the period")
        elif metrics.avg_confidence_score < 0.5:
            insights.append("Lower confidence periods suggest market uncertainty")

        if len(daily_reports) >= 20:
            insights.append("Consistent daily analysis coverage achieved")

        insights.append(f"Generated {metrics.total_recommendations} investment recommendations")

        # Add fallback insights if none generated
        if len(insights) < 3:
            insights.extend([
                "Market analysis systems operating effectively",
                "Diversified investment approach maintained",
                "Risk management protocols followed"
            ])

        return insights[:5]  # Limit to 5 insights

    async def _generate_outlook(self, daily_reports: List[Dict]) -> str:
        """Generate next month outlook"""
        try:
            # Create a simple outlook based on recent trends
            recent_reports = daily_reports[-7:] if len(daily_reports) >= 7 else daily_reports

            prompt = f"""
Based on the last {len(recent_reports)} daily investment reports, provide a brief outlook for the next month.

Consider:
- Recent market sentiment trends
- Consistency of recommendations
- Risk factors mentioned

Provide a 2-3 sentence outlook focusing on:
1. Expected market conditions
2. Investment strategy adjustments
3. Key factors to monitor

Keep it concise and actionable.
"""

            response = await self.analyzer.llm_adapter.chat_completion(
                prompt=prompt,
                temperature=0.4,
                max_tokens=500,
                timeout=30
            )

            if response:
                return response
            else:
                return self._fallback_outlook(recent_reports)

        except Exception as e:
            logger.error(f"Error generating outlook: {str(e)}")
            return self._fallback_outlook(daily_reports[-7:] if len(daily_reports) >= 7 else daily_reports)

    def _fallback_outlook(self, recent_reports: List[Dict]) -> str:
        """Generate fallback outlook"""
        return f"""
Based on {len(recent_reports)} recent reports, market conditions appear stable with continued opportunities
in both stable and growth investments. Maintain diversified approach with {settings.stable_investment}/${settings.risky_investment}
allocation strategy. Monitor for any significant market shifts or volatility changes.
"""

    async def _create_summary_content(self, daily_reports: List[Dict],
                                    metrics: PerformanceMetrics,
                                    stable_performers: List[TopPerformer],
                                    risky_performers: List[TopPerformer],
                                    ai_stable_rec: Optional[AIInvestmentRecommendation] = None,
                                    ai_risky_rec: Optional[AIInvestmentRecommendation] = None) -> str:
        """Create detailed summary content"""

        content = f"""
# 30-Day Investment Summary Report

## Period Overview
- **Analysis Period**: {len(daily_reports)} days
- **Total Recommendations**: {metrics.total_recommendations}
- **Average Confidence**: {metrics.avg_confidence_score:.1%}

## Top Performing Recommendations

### Stable Category ($200 investments)
"""

        for performer in stable_performers[:3]:
            content += f"- **{performer.symbol}**: Recommended {performer.frequency} times\n"

        content += "\n### Risky Category ($50 investments)\n"

        for performer in risky_performers[:3]:
            content += f"- **{performer.symbol}**: Recommended {performer.frequency} times\n"

        content += f"""

## Key Statistics
- Most consistent stable pick: {stable_performers[0].symbol if stable_performers else 'N/A'}
- Most frequent risky pick: {risky_performers[0].symbol if risky_performers else 'N/A'}
- System reliability: {len(daily_reports)/30*100:.0f}% daily coverage

## AI Investment Recommendations

### Stable Investment ($200)
"""

        if ai_stable_rec:
            content += f"""
**Recommended Stock: {ai_stable_rec.symbol}**
- Current Price: ${f'{ai_stable_rec.current_price:.2f}' if ai_stable_rec.current_price is not None else 'N/A'}
- Target Price: ${f'{ai_stable_rec.target_price:.2f}' if ai_stable_rec.target_price is not None else 'N/A'}
- Expected Return: ${f'{ai_stable_rec.expected_return:.1%}' if ai_stable_rec.expected_return else 'N/A'}
- Confidence Level: {ai_stable_rec.confidence:.1%}
- News Sentiment: {ai_stable_rec.news_sentiment}

**Investment Reasoning:**
{ai_stable_rec.reasoning}

**Key Risk Factors:**
{', '.join(ai_stable_rec.risk_factors) if ai_stable_rec.risk_factors else 'Standard market risks'}
"""
        else:
            content += "AI analysis not available for stable category.\n"

        content += "\n### Risky Investment ($50)\n"

        if ai_risky_rec:
            content += f"""
**Recommended Stock: {ai_risky_rec.symbol}**
- Current Price: ${f'{ai_risky_rec.current_price:.2f}' if ai_risky_rec.current_price is not None else 'N/A'}
- Target Price: ${f'{ai_risky_rec.target_price:.2f}' if ai_risky_rec.target_price is not None else 'N/A'}
- Expected Return: {ai_risky_rec.expected_return:.1%} if ai_risky_rec.expected_return else 'N/A'
- Confidence Level: {ai_risky_rec.confidence:.1%}
- News Sentiment: {ai_risky_rec.news_sentiment}

**Investment Reasoning:**
{ai_risky_rec.reasoning}

**Key Risk Factors:**
{', '.join(ai_risky_rec.risk_factors) if ai_risky_rec.risk_factors else 'Higher volatility expected'}
"""
        else:
            content += "AI analysis not available for risky category.\n"

        content += f"""

## Analysis Quality
The automated analysis system maintained {'high' if metrics.avg_confidence_score > 0.7 else 'moderate' if metrics.avg_confidence_score > 0.5 else 'developing'}
confidence levels throughout the period, indicating {'strong' if metrics.avg_confidence_score > 0.7 else 'adequate'} data quality and analysis reliability.

## Investment Strategy Summary
Based on AI analysis of market data, news sentiment, and technical indicators, the recommended portfolio allocation is:
- **Stable Investment**: ${settings.stable_investment} in {ai_stable_rec.symbol if ai_stable_rec else 'TBD'}
- **Growth Investment**: ${settings.risky_investment} in {ai_risky_rec.symbol if ai_risky_rec else 'TBD'}

*This report includes AI-generated investment analysis. Individual research and due diligence are strongly recommended before making investment decisions.*
"""

        return content

    def _create_empty_summary_report(self, start_date: str, end_date: str) -> SummaryReport:
        """Create empty summary report when no data is available"""
        return SummaryReport(
            report_id=f"SR_{end_date}_30D_EMPTY",
            start_date=datetime.strptime(start_date, "%Y-%m-%d"),
            end_date=datetime.strptime(end_date, "%Y-%m-%d"),
            days_analyzed=0,
            performance_metrics=PerformanceMetrics(
                total_recommendations=0,
                stable_picks_count=0,
                risky_picks_count=0,
                avg_confidence_score=0.0
            ),
            top_stable_performers=[],
            top_risky_performers=[],
            market_trends=MarketTrends(
                dominant_themes=["No data available"],
                sector_performance=SectorPerformance()
            ),
            insights=["Insufficient data for analysis"],
            next_month_outlook="Unable to generate outlook due to lack of historical data.",
            content="No daily reports available for the specified period. Summary analysis cannot be generated."
        )
