from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime, timedelta
from typing import Optional

from ..services.json_storage import JSONStorage
from ..services.report_generator import ReportGenerator
from ..models.reports import CurrentRecommendations, ReportRequest
from ..config import settings

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

storage = JSONStorage()
report_generator = ReportGenerator()


@router.get("/daily/latest")
async def get_latest_daily_report():
    """Get the most recent daily report"""
    try:
        # Try today first, then yesterday
        today = datetime.now().strftime("%Y-%m-%d")
        report = await storage.get_daily_report(today)
        
        if not report:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            report = await storage.get_daily_report(yesterday)
            
            if not report:
                raise HTTPException(
                    status_code=404,
                    detail="No recent daily reports available"
                )
        
        return {
            "report": report,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving latest report: {str(e)}"
        )


@router.get("/daily/{date}")
async def get_daily_report(date: str):
    """Get daily report for a specific date (YYYY-MM-DD format)"""
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        report = await storage.get_daily_report(date)
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Daily report not found for {date}"
            )
        
        return {
            "report": report,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving daily report: {str(e)}"
        )


@router.post("/summary")
async def generate_summary_report(
    background_tasks: BackgroundTasks,
    request: ReportRequest
):
    """Generate a summary report for the specified date range"""
    try:
        # Validate date range
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Check if date range is not too large (max 60 days)
        date_diff = (request.end_date - request.start_date).days
        if date_diff > 60:
            raise HTTPException(
                status_code=400,
                detail="Date range cannot exceed 60 days"
            )
        
        # Generate report in background
        start_date_str = request.start_date.strftime("%Y-%m-%d")
        end_date_str = request.end_date.strftime("%Y-%m-%d")
        
        # For now, generate synchronously. In production, use background tasks
        summary_report = await report_generator.create_summary_report(
            start_date_str, end_date_str
        )
        
        return {
            "message": "Summary report generated successfully",
            "report_id": summary_report.report_id,
            "report": summary_report.model_dump(),
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary report: {str(e)}"
        )


@router.get("/summary/latest")
async def get_latest_summary_report():
    """Get the latest summary report"""
    try:
        from pathlib import Path
        import json
        import os
        
        summaries_dir = Path("data/summaries")
        if not summaries_dir.exists():
            raise HTTPException(
                status_code=404,
                detail="No summary reports directory found"
            )
        
        # Find the most recent summary report (both SR_ and MR_ files)
        summary_files = list(summaries_dir.glob("*R_*.json"))
        if not summary_files:
            raise HTTPException(
                status_code=404,
                detail="No summary reports found"
            )
        
        # Sort by modification time and get the latest
        latest_file = max(summary_files, key=os.path.getmtime)
        
        with open(latest_file, 'r') as f:
            summary_report = json.load(f)
        
        return {
            "report": summary_report,
            "file_path": str(latest_file),
            "generated_at": summary_report.get('generated_at'),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving latest summary report: {str(e)}"
        )


@router.get("/summary/{report_id}")
async def get_summary_report(report_id: str):
    """Get a specific summary report"""
    try:
        # Look for the summary report file
        from pathlib import Path
        report_file = Path("data/summaries") / f"{report_id}.json"
        
        if not report_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Summary report {report_id} not found"
            )
        
        import json
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        return {
            "report": report,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving summary report: {str(e)}"
        )


@router.get("/current-recommendations")
async def get_current_recommendations():
    """Get current investment recommendations"""
    try:
        # Get latest daily report
        today = datetime.now().strftime("%Y-%m-%d")
        report = await storage.get_daily_report(today)
        
        if not report:
            # Try yesterday
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            report = await storage.get_daily_report(yesterday)
            
            if not report:
                raise HTTPException(
                    status_code=404,
                    detail="No recent recommendations available"
                )
        
        # Extract recommendations
        stable_rec = report.get('stable_recommendation', {})
        risky_rec = report.get('risky_recommendation', {})
        market_overview = report.get('market_overview', {})
        
        recommendations = CurrentRecommendations(
            date=datetime.fromisoformat(report['date']),
            stable_recommendation={
                "symbol": stable_rec.get('symbol', 'N/A'),
                "allocation": stable_rec.get('allocation', settings.stable_investment),
                "reasoning": stable_rec.get('reasoning', 'No reasoning available'),
                "confidence": stable_rec.get('confidence', 0.5),
                "expected_return_30d": stable_rec.get('expected_return_30d')
            },
            risky_recommendation={
                "symbol": risky_rec.get('symbol', 'N/A'),
                "allocation": risky_rec.get('allocation', settings.risky_investment),
                "reasoning": risky_rec.get('reasoning', 'No reasoning available'),
                "confidence": risky_rec.get('confidence', 0.5),
                "expected_return_30d": risky_rec.get('expected_return_30d')
            },
            market_context=market_overview.get('market_sentiment', 'Unknown market conditions')
        )
        
        return recommendations.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving current recommendations: {str(e)}"
        )


@router.get("/history")
async def get_reports_history(
    days: int = 30,
    report_type: str = "DAILY"
):
    """Get history of reports"""
    try:
        if report_type.upper() not in ["DAILY", "SUMMARY"]:
            raise HTTPException(
                status_code=400,
                detail="Report type must be 'DAILY' or 'SUMMARY'"
            )
        
        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get reports from JSON storage
        if report_type.upper() == "DAILY":
            reports = await storage.get_daily_reports_range(start_date, end_date)
        else:
            # For summary reports, we'd need to implement a similar range query
            # For now, return empty list
            reports = []
        
        return {
            "report_type": report_type.upper(),
            "period_days": days,
            "total_reports": len(reports),
            "reports": reports
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving reports history: {str(e)}"
        )


@router.get("/performance")
async def get_performance_summary():
    """Get performance summary of recommendations"""
    try:
        # Get last 30 days of daily reports
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        reports = await storage.get_daily_reports_range(start_date, end_date)
        
        if not reports:
            return {
                "message": "No reports available for performance analysis",
                "period": "30 days",
                "total_reports": 0
            }
        
        # Analyze performance metrics
        stable_symbols = []
        risky_symbols = []
        confidence_scores = []
        
        for report in reports:
            if 'stable_recommendation' in report:
                stable_rec = report['stable_recommendation']
                stable_symbols.append(stable_rec.get('symbol'))
                confidence_scores.append(stable_rec.get('confidence', 0.5))
            
            if 'risky_recommendation' in report:
                risky_rec = report['risky_recommendation']
                risky_symbols.append(risky_rec.get('symbol'))
                confidence_scores.append(risky_rec.get('confidence', 0.5))
        
        # Calculate statistics
        from collections import Counter
        stable_counts = Counter(stable_symbols)
        risky_counts = Counter(risky_symbols)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "period": "30 days",
            "total_reports": len(reports),
            "average_confidence": round(avg_confidence, 3),
            "most_recommended": {
                "stable": stable_counts.most_common(3),
                "risky": risky_counts.most_common(3)
            },
            "system_reliability": len(reports) / 30 * 100  # Percentage of days with reports
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating performance summary: {str(e)}"
        )



@router.get("/summary/latest/ai-recommendations")
async def get_latest_ai_recommendations():
    """Get AI recommendations from the latest summary report"""
    try:
        # Get the most recent summary report
        from pathlib import Path
        import json
        import os
        
        summaries_dir = Path("data/summaries")
        if not summaries_dir.exists():
            raise HTTPException(
                status_code=404,
                detail="No summary reports directory found"
            )
        
        # Find the most recent summary report
        summary_files = list(summaries_dir.glob("SR_*.json"))
        if not summary_files:
            raise HTTPException(
                status_code=404,
                detail="No summary reports found"
            )
        
        # Sort by modification time and get the latest
        latest_file = max(summary_files, key=os.path.getmtime)
        
        with open(latest_file, 'r') as f:
            summary_report = json.load(f)
        
        # Extract AI recommendations
        ai_stable = summary_report.get('ai_stable_recommendation')
        ai_risky = summary_report.get('ai_risky_recommendation')
        
        if not ai_stable and not ai_risky:
            raise HTTPException(
                status_code=404,
                detail="No AI recommendations found in latest summary report"
            )
        
        return {
            "report_id": summary_report.get('report_id'),
            "generated_at": summary_report.get('end_date'),
            "days_analyzed": summary_report.get('days_analyzed', 0),
            "ai_stable_recommendation": ai_stable,
            "ai_risky_recommendation": ai_risky,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving AI recommendations: {str(e)}"
        )