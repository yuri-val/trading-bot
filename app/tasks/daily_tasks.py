from celery import Celery
from datetime import datetime, timedelta
import asyncio
import logging
from typing import List

from ..config import settings
from ..services.data_collector import DataCollector
from ..services.analyzer import LLMAnalyzer
from ..services.json_storage import JSONStorage
from ..services.report_generator import ReportGenerator
from ..models.stock_data import StockData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'trading_bot',
    broker=f'redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}',
    backend=f'redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}'
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'trading_bot.daily_analysis_task': {'queue': 'analysis'},
        'trading_bot.generate_summary_report_task': {'queue': 'reports'},
        'trading_bot.health_check_task': {'queue': 'monitoring'},
        'trading_bot.test_task': {'queue': 'testing'},
    }
)


@celery_app.task(bind=True, name='trading_bot.daily_analysis_task')
def daily_analysis_task(self):
    """Daily analysis task - runs at 09:00 UTC (12:00 Kyiv time)"""

    async def run_analysis():
        try:
            logger.info(f"[{datetime.now()}] Starting daily analysis task...")

            # Initialize services
            collector = DataCollector()
            analyzer = LLMAnalyzer()
            storage = JSONStorage()
            report_gen = ReportGenerator()

            # Collect data for all stocks (this will also update stock lists)
            logger.info("Phase 1: Collecting stock data and updating stock lists...")
            stock_data = await collector.collect_daily_data()

            # Get the updated watchlist for logging
            watchlist = await collector.get_watchlist()
            logger.info(f"Analyzed {len(stock_data)} stocks: {len(watchlist['stable'])} stable, {len(watchlist['risky'])} risky")

            if not stock_data:
                logger.error("No stock data collected. Aborting analysis.")
                return {"status": "failed", "reason": "No data collected"}

            logger.info(f"Successfully collected data for {len(stock_data)} stocks")

            # Analyze each stock with LLM
            logger.info("Phase 2: Running LLM analysis...")
            analyzed_stocks: List[StockData] = []

            for symbol, data in stock_data.items():
                try:
                    logger.info(f"Analyzing {symbol}...")
                    analysis = await analyzer.analyze_stock_data(data)

                    if analysis:
                        data.ai_analysis = analysis
                        analyzed_stocks.append(data)

                        # Data is already saved to JSON storage in collect_daily_data
                        # Just update with AI analysis
                        await storage.save_stock_data(data)

                        logger.info(f"✓ {symbol}: {analysis.recommendation.value} "
                                  f"(confidence: {analysis.confidence_level:.2f})")
                    else:
                        logger.warning(f"✗ {symbol}: Analysis failed")

                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {str(e)}")
                    continue

            logger.info(f"Completed analysis for {len(analyzed_stocks)} stocks")

            # Generate daily report
            logger.info("Phase 3: Generating daily report...")
            daily_report = await report_gen.create_daily_report(analyzed_stocks)

            logger.info(f"Daily report generated: {daily_report.report_id}")
            logger.info(f"Stable recommendation: {daily_report.stable_recommendation.symbol}")
            logger.info(f"Risky recommendation: {daily_report.risky_recommendation.symbol}")

            # Update task status
            self.update_state(
                state='SUCCESS',
                meta={
                    'analyzed_stocks': len(analyzed_stocks),
                    'stable_pick': daily_report.stable_recommendation.symbol,
                    'risky_pick': daily_report.risky_recommendation.symbol,
                    'processing_time': daily_report.processing_time_minutes,
                    'completed_at': datetime.now().isoformat()
                }
            )

            logger.info(f"[{datetime.now()}] Daily analysis completed successfully!")

            return {
                "status": "success",
                "analyzed_stocks": len(analyzed_stocks),
                "report_id": daily_report.report_id,
                "stable_recommendation": daily_report.stable_recommendation.symbol,
                "risky_recommendation": daily_report.risky_recommendation.symbol,
                "processing_time_minutes": daily_report.processing_time_minutes
            }

        except Exception as e:
            logger.error(f"Daily analysis failed: {str(e)}")
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e),
                    'failed_at': datetime.now().isoformat()
                }
            )
            return {"status": "failed", "error": str(e)}

    # Run the async analysis
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_analysis())
    finally:
        loop.close()


@celery_app.task(bind=True, name='trading_bot.generate_summary_report_task')
def generate_summary_report_task(self, start_date: str = None, end_date: str = None):
    """Generate summary report task"""

    async def run_summary():
        try:
            logger.info(f"[{datetime.now()}] Starting summary report generation...")

            # Initialize services
            storage = JSONStorage()
            report_gen = ReportGenerator()

            # Use provided dates or default to last 30 days
            if not end_date:
                end = datetime.now()
            else:
                end = datetime.strptime(end_date, "%Y-%m-%d")

            if not start_date:
                start = end - timedelta(days=30)
            else:
                start = datetime.strptime(start_date, "%Y-%m-%d")

            start_date_str = start.strftime("%Y-%m-%d")
            end_date_str = end.strftime("%Y-%m-%d")

            logger.info(f"Generating summary report for period: {start_date_str} to {end_date_str}")

            # Generate summary report
            summary_report = await report_gen.create_summary_report(start_date_str, end_date_str)

            logger.info(f"Summary report generated: {summary_report.report_id}")
            logger.info(f"Days analyzed: {summary_report.days_analyzed}")
            logger.info(f"Total recommendations: {summary_report.performance_metrics.total_recommendations}")

            # Update task status
            self.update_state(
                state='SUCCESS',
                meta={
                    'report_id': summary_report.report_id,
                    'days_analyzed': summary_report.days_analyzed,
                    'total_recommendations': summary_report.performance_metrics.total_recommendations,
                    'completed_at': datetime.now().isoformat()
                }
            )

            logger.info(f"[{datetime.now()}] Summary report generation completed!")

            return {
                "status": "success",
                "report_id": summary_report.report_id,
                "days_analyzed": summary_report.days_analyzed,
                "total_recommendations": summary_report.performance_metrics.total_recommendations
            }

        except Exception as e:
            logger.error(f"Summary report generation failed: {str(e)}")
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e),
                    'failed_at': datetime.now().isoformat()
                }
            )
            return {"status": "failed", "error": str(e)}

    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_summary())
    finally:
        loop.close()


@celery_app.task(name='trading_bot.test_task')
def test_task():
    """Test task to verify Celery is working"""
    logger.info("Test task executed successfully!")
    return {
        "status": "success",
        "message": "Celery is working correctly",
        "timestamp": datetime.now().isoformat()
    }


@celery_app.task(name='trading_bot.health_check_task')
def health_check_task():
    """Health check task for monitoring"""
    try:
        # Basic health checks
        checks = {
            "celery_worker": "healthy",
            "timestamp": datetime.now().isoformat(),
            "redis_connection": "unknown",
            "storage_status": "unknown"
        }

        # Test Redis connection (Celery broker)
        try:
            celery_app.control.inspect().ping()
            checks["redis_connection"] = "healthy"
        except Exception as e:
            checks["redis_connection"] = f"error: {str(e)}"

        # Test JSON storage
        try:
            storage = JSONStorage()
            storage_health = storage.get_health_status()
            checks["storage_status"] = storage_health.get("status", "unknown")
        except Exception as e:
            checks["storage_status"] = f"error: {str(e)}"

        return checks

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Manual task execution functions (for testing)
def run_daily_analysis_now():
    """Manually trigger daily analysis (for testing)"""
    logger.info("Manually triggering daily analysis...")
    result = daily_analysis_task.delay()
    return result


def run_summary_report_now(days: int = 30):
    """Manually trigger summary report generation (for testing)"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    logger.info(f"Manually triggering summary report for {start_date} to {end_date}")
    result = generate_summary_report_task.delay(start_date, end_date)
    return result


if __name__ == "__main__":
    # For manual testing
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "daily":
            print("Running daily analysis...")
            result = run_daily_analysis_now()
            print(f"Task ID: {result.id}")
        elif sys.argv[1] == "summary":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            print(f"Running summary report for last {days} days...")
            result = run_summary_report_now(days)
            print(f"Task ID: {result.id}")
        elif sys.argv[1] == "test":
            print("Running test task...")
            result = test_task.delay()
            print(f"Task ID: {result.id}")
    else:
        print("Usage: python daily_tasks.py [daily|summary|test]")
