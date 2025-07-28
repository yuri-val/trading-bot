from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..services.json_storage import JSONStorage
from ..services.data_collector import DataCollector
from ..models.stock_data import StockData

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])

storage = JSONStorage()
data_collector = DataCollector()


@router.get("/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    """Get detailed analysis of a specific stock"""
    try:
        # Get latest stock data from JSON storage
        stock_data = await storage.get_latest_stock_data(symbol.upper())
        
        if not stock_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No analysis data found for {symbol.upper()}"
            )
        
        return {
            "symbol": symbol.upper(),
            "last_updated": stock_data.get("date"),
            "data": stock_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving stock analysis: {str(e)}"
        )


@router.get("/{symbol}/history")
async def get_stock_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to retrieve")
):
    """Get historical analysis data for a stock"""
    try:
        # Get historical data from JSON storage
        history = await storage.get_stock_history(symbol.upper(), days)
        
        return {
            "symbol": symbol.upper(),
            "period_days": days,
            "data_points": len(history),
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stock history: {str(e)}"
        )


@router.get("/watchlist")
async def get_watchlist():
    """Get the complete stock watchlist"""
    try:
        watchlist = await data_collector.get_watchlist()
        
        return {
            "total_stocks": len(watchlist["stable"]) + len(watchlist["risky"]),
            "stable_stocks": {
                "count": len(watchlist["stable"]),
                "symbols": watchlist["stable"]
            },
            "risky_stocks": {
                "count": len(watchlist["risky"]),
                "symbols": watchlist["risky"]
            },
            "last_updated": watchlist.get("last_updated")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving watchlist: {str(e)}"
        )


@router.get("/categories/{category}")
async def get_stocks_by_category(category: str):
    """Get all stocks in a specific category (stable or risky)"""
    try:
        category_upper = category.upper()
        if category_upper not in ["STABLE", "RISKY"]:
            raise HTTPException(
                status_code=400,
                detail="Category must be either 'stable' or 'risky'"
            )
        
        watchlist = await data_collector.get_watchlist()
        category_key = "stable" if category_upper == "STABLE" else "risky"
        symbols = watchlist[category_key]
        
        # Get latest data for all symbols in category
        latest_data = []
        for symbol in symbols:
            stock_data = await storage.get_latest_stock_data(symbol)
            if stock_data:
                latest_data.append(stock_data)
        
        return {
            "category": category_upper,
            "total_symbols": len(symbols),
            "symbols_with_data": len(latest_data),
            "stocks": latest_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stocks by category: {str(e)}"
        )


@router.get("/trending")
async def get_trending_stocks(
    limit: int = Query(default=10, ge=1, le=50, description="Number of stocks to return")
):
    """Get trending stocks based on recent price movements"""
    try:
        # Get latest data from today
        today = datetime.now().strftime("%Y-%m-%d")
        stocks_today = await storage.get_stocks_by_date(today)
        
        # Sort by change percentage and limit results
        trending_stocks = sorted(
            stocks_today, 
            key=lambda x: x.get('price_data', {}).get('change_percent', 0), 
            reverse=True
        )[:limit]
        
        trending = []
        for stock_data in trending_stocks:
            trending.append({
                "symbol": stock_data['symbol'],
                "change_percent": stock_data['price_data']['change_percent'],
                "current_price": stock_data['price_data']['close'],
                "volume": stock_data['price_data']['volume'],
                "category": stock_data['category'],
                "last_updated": stock_data['date']
            })
        
        return {
            "trending_stocks": trending,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving trending stocks: {str(e)}"
        )


@router.get("/{symbol}/recommendation")
async def get_stock_recommendation(symbol: str):
    """Get current AI recommendation for a specific stock"""
    try:
        stock_data = await storage.get_latest_stock_data(symbol.upper())
        
        if not stock_data:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {symbol.upper()}"
            )
        
        ai_analysis = stock_data.get('ai_analysis')
        if not ai_analysis:
            raise HTTPException(
                status_code=404,
                detail=f"No AI analysis available for {symbol.upper()}"
            )
        
        return {
            "symbol": symbol.upper(),
            "recommendation": ai_analysis.get('recommendation'),
            "confidence_level": ai_analysis.get('confidence_level'),
            "target_allocation": ai_analysis.get('target_allocation'),
            "price_target_30d": ai_analysis.get('price_target_30d'),
            "risk_score": ai_analysis.get('risk_score'),
            "key_factors": ai_analysis.get('key_factors', []),
            "reasoning": ai_analysis.get('reasoning'),
            "last_analyzed": stock_data.get('date')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving recommendation: {str(e)}"
        )