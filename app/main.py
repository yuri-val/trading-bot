from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import logging

from .config import settings
from .api import stocks, reports
from .services.json_storage import JSONStorage
from .services.data_collector import DataCollector

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

# Mount static files for the web UI (if directory exists)
import os
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
storage = JSONStorage()
data_collector = DataCollector()


@app.get("/")
async def root():
    """Serve the main UI"""
    if os.path.exists('static/index.html'):
        return FileResponse('static/index.html')
    elif os.path.exists('app/templates/dashboard.html'):
        return FileResponse('app/templates/dashboard.html')
    else:
        return {
            "message": "Trading Bot API",
            "version": "1.0.0", 
            "description": "Automated stock analysis and investment recommendations",
            "note": "Web UI not available - templates not found",
            "endpoints": {
                "docs": "/docs",
                "stocks": "/api/v1/stocks",
                "reports": "/api/v1/reports",
                "health": "/health"
            }
        }

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "message": "Trading Bot API",
        "version": "1.0.0",
        "description": "Automated stock analysis and investment recommendations",
        "endpoints": {
            "docs": "/docs",
            "stocks": "/api/v1/stocks",
            "reports": "/api/v1/reports",
            "health": "/health",
            "ui": "/"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check JSON storage health
        storage_health = storage.get_health_status()
        
        # Get current watchlist info
        watchlist = await data_collector.get_watchlist()
        
        # Basic system health
        system_health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "api": "operational",
                "storage": storage_health.get("status", "unknown")
            },
            "configuration": {
                "stable_stocks_count": len(watchlist["stable"]),
                "risky_stocks_count": len(watchlist["risky"]),
                "stable_allocation": settings.stable_investment,
                "risky_allocation": settings.risky_investment,
                "stock_lists_last_updated": watchlist.get("last_updated")
            }
        }
        
        # Determine overall health
        if storage_health.get("status") == "error":
            system_health["status"] = "degraded"
            system_health["warnings"] = ["JSON storage system issues"]
        
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
    watchlist = await data_collector.get_watchlist()
    
    return {
        "watchlist": {
            "stable_stocks": watchlist["stable"],
            "risky_stocks": watchlist["risky"],
            "last_updated": watchlist.get("last_updated")
        },
        "investment_allocation": {
            "stable_amount": settings.stable_investment,
            "risky_amount": settings.risky_investment,
            "total_monthly": settings.stable_investment + settings.risky_investment
        },
        "analysis_settings": {
            "confidence_threshold": settings.confidence_threshold,
            "max_news_articles": settings.max_news_articles,
            "analysis_timeout": settings.analysis_timeout,
            "max_stable_stocks": settings.max_stable_stocks,
            "max_risky_stocks": settings.max_risky_stocks
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
        todays_report = await storage.get_daily_report(today)
        yesterdays_report = await storage.get_daily_report(yesterday)
        
        # Get storage stats
        storage_stats = await storage.get_storage_stats()
        storage_health = storage.get_health_status()
        
        # Get current watchlist
        watchlist = await data_collector.get_watchlist()
        
        return {
            "system_time": datetime.now().isoformat(),
            "analysis_status": {
                "todays_report_available": todays_report is not None,
                "yesterdays_report_available": yesterdays_report is not None,
                "last_analysis": todays_report.get('date') if todays_report else yesterdays_report.get('date') if yesterdays_report else None
            },
            "storage_status": storage_health,
            "storage_stats": storage_stats,
            "api_configuration": {
                "total_tracked_stocks": len(watchlist["stable"]) + len(watchlist["risky"]),
                "investment_strategy": f"${settings.stable_investment} stable + ${settings.risky_investment} risky",
                "stock_lists_last_updated": watchlist.get("last_updated")
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
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Trading Bot API starting up...")
    
    # Check for existing stock lists (non-blocking)
    try:
        # Try to load existing lists without triggering internet updates
        loaded = await data_collector.stock_collector.load_lists_from_file()
        if loaded:
            current_lists = data_collector.stock_collector.get_current_lists()
            logger.info(f"Loaded existing stock lists: {len(current_lists['stable'])} stable, {len(current_lists['risky'])} risky stocks")
            if current_lists.get('last_updated'):
                logger.info(f"Stock lists last updated: {current_lists['last_updated']}")
        else:
            logger.info("No existing stock lists found - will be updated during first daily analysis")
    except Exception as e:
        logger.warning(f"Could not load existing stock lists: {str(e)}")
    
    logger.info(f"Investment allocation: ${settings.stable_investment} stable, ${settings.risky_investment} risky")
    
    # Test storage health
    try:
        health = storage.get_health_status()
        logger.info(f"JSON storage status: {health.get('status', 'unknown')}")
    except Exception as e:
        logger.warning(f"Storage system issue: {str(e)}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Trading Bot API shutting down...")
    
    # Optional: perform cleanup tasks
    try:
        # Clean up old data if needed
        await storage.cleanup_old_data()
    except Exception as e:
        logger.warning(f"Cleanup warning: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )