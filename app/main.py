from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import logging

from .config import settings
from .api import stocks, reports
from .services.opensearch_client import OpenSearchClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Trading Bot API",
    description="Automated stock analysis and investment recommendation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stocks.router)
app.include_router(reports.router)

# Initialize services
opensearch_client = OpenSearchClient()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Trading Bot API",
        "version": "1.0.0",
        "description": "Automated stock analysis and investment recommendations",
        "endpoints": {
            "docs": "/docs",
            "stocks": "/api/v1/stocks",
            "reports": "/api/v1/reports",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check OpenSearch connection
        opensearch_health = await opensearch_client.get_health_status()
        
        # Basic system health
        system_health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "api": "operational",
                "opensearch": opensearch_health.get("status", "unknown")
            },
            "configuration": {
                "stable_stocks_count": len(settings.stable_stocks),
                "risky_stocks_count": len(settings.risky_stocks),
                "stable_allocation": settings.stable_investment,
                "risky_allocation": settings.risky_investment
            }
        }
        
        # Determine overall health
        if opensearch_health.get("status") == "red":
            system_health["status"] = "degraded"
            system_health["warnings"] = ["OpenSearch cluster health is red"]
        elif opensearch_health.get("status") == "yellow":
            system_health["status"] = "warning"
            system_health["warnings"] = ["OpenSearch cluster health is yellow"]
        
        return system_health
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@app.get("/api/v1/config")
async def get_config():
    """Get system configuration (non-sensitive data only)"""
    return {
        "watchlist": {
            "stable_stocks": settings.stable_stocks,
            "risky_stocks": settings.risky_stocks
        },
        "investment_allocation": {
            "stable_amount": settings.stable_investment,
            "risky_amount": settings.risky_investment,
            "total_monthly": settings.stable_investment + settings.risky_investment
        },
        "analysis_settings": {
            "confidence_threshold": settings.confidence_threshold,
            "max_news_articles": settings.max_news_articles,
            "analysis_timeout": settings.analysis_timeout
        }
    }


@app.get("/api/v1/status")
async def get_system_status():
    """Get detailed system status"""
    try:
        # Get recent analysis data
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Check for today's report
        todays_report = await opensearch_client.get_daily_report(today)
        yesterdays_report = await opensearch_client.get_daily_report(yesterday)
        
        # Get OpenSearch health
        opensearch_health = await opensearch_client.get_health_status()
        
        return {
            "system_time": datetime.now().isoformat(),
            "analysis_status": {
                "todays_report_available": todays_report is not None,
                "yesterdays_report_available": yesterdays_report is not None,
                "last_analysis": todays_report.get('date') if todays_report else yesterdays_report.get('date') if yesterdays_report else None
            },
            "database_status": opensearch_health,
            "api_configuration": {
                "total_tracked_stocks": len(settings.stable_stocks) + len(settings.risky_stocks),
                "investment_strategy": f"${settings.stable_investment} stable + ${settings.risky_investment} risky"
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return {
            "error": str(e),
            "system_time": datetime.now().isoformat(),
            "status": "error"
        }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": "The requested resource was not found",
        "timestamp": datetime.now().isoformat()
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "timestamp": datetime.now().isoformat()
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Trading Bot API starting up...")
    logger.info(f"Tracking {len(settings.stable_stocks)} stable and {len(settings.risky_stocks)} risky stocks")
    logger.info(f"Investment allocation: ${settings.stable_investment} stable, ${settings.risky_investment} risky")
    
    # Test OpenSearch connection
    try:
        health = await opensearch_client.get_health_status()
        logger.info(f"OpenSearch status: {health.get('status', 'unknown')}")
    except Exception as e:
        logger.warning(f"OpenSearch connection issue: {str(e)}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Trading Bot API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )