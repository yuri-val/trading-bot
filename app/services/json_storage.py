import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..models.stock_data import StockData
from ..models.reports import DailyReport, SummaryReport

logger = logging.getLogger(__name__)


class JSONStorage:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.data_dir / "stocks").mkdir(exist_ok=True)
        (self.data_dir / "reports").mkdir(exist_ok=True)
        (self.data_dir / "summaries").mkdir(exist_ok=True)
    
    async def save_stock_data(self, stock_data: StockData) -> bool:
        """Save stock data to JSON file"""
        try:
            date_str = stock_data.date.strftime("%Y-%m-%d")
            filename = f"{date_str}_{stock_data.symbol}.json"
            filepath = self.data_dir / "stocks" / filename
            
            # Convert to dict and handle datetime serialization
            data = stock_data.model_dump()
            data['date'] = stock_data.date.isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved stock data: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving stock data for {stock_data.symbol}: {str(e)}")
            return False
    
    async def get_latest_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get latest stock data for a symbol"""
        try:
            # Look for files with this symbol, get the most recent
            stock_files = list(self.data_dir.glob(f"stocks/*_{symbol}.json"))
            if not stock_files:
                return None
            
            # Sort by date (filename contains date)
            latest_file = sorted(stock_files)[-1]
            
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting latest stock data for {symbol}: {str(e)}")
            return None
    
    async def get_stocks_by_date(self, date: str) -> List[Dict]:
        """Get all stock data for a specific date"""
        try:
            pattern = f"stocks/{date}_*.json"
            stock_files = list(self.data_dir.glob(pattern))
            
            stocks = []
            for file in stock_files:
                with open(file, 'r') as f:
                    data = json.load(f)
                    stocks.append(data)
            
            return stocks
            
        except Exception as e:
            logger.error(f"Error getting stocks for date {date}: {str(e)}")
            return []
    
    async def save_daily_report(self, report: DailyReport) -> bool:
        """Save daily report to JSON file"""
        try:
            filename = f"{report.report_id}.json"
            filepath = self.data_dir / "reports" / filename
            
            # Convert to dict and handle datetime serialization
            data = report.model_dump()
            data['date'] = report.date.isoformat()
            data['market_overview']['date'] = report.market_overview.date.isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved daily report: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving daily report: {str(e)}")
            return False
    
    async def get_daily_report(self, date: str) -> Optional[Dict]:
        """Get daily report for a specific date"""
        try:
            filename = f"DR_{date}.json"
            filepath = self.data_dir / "reports" / filename
            
            if not filepath.exists():
                return None
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting daily report for {date}: {str(e)}")
            return None
    
    async def save_summary_report(self, report: SummaryReport) -> bool:
        """Save summary report to JSON file"""
        try:
            filename = f"{report.report_id}.json"
            filepath = self.data_dir / "summaries" / filename
            
            # Convert to dict and handle datetime serialization
            data = report.model_dump()
            data['start_date'] = report.start_date.isoformat()
            data['end_date'] = report.end_date.isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved summary report: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving summary report: {str(e)}")
            return False
    
    async def get_daily_reports_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get daily reports within date range"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            reports = []
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                report = await self.get_daily_report(date_str)
                if report:
                    reports.append(report)
                current += timedelta(days=1)
            
            return reports
            
        except Exception as e:
            logger.error(f"Error getting daily reports range: {str(e)}")
            return []
    
    async def get_all_stock_symbols(self) -> List[str]:
        """Get all unique stock symbols from stored data"""
        try:
            stock_files = list(self.data_dir.glob("stocks/*.json"))
            symbols = set()
            
            for file in stock_files:
                # Extract symbol from filename: YYYY-MM-DD_SYMBOL.json
                symbol = file.stem.split('_', 1)[1]
                symbols.add(symbol)
            
            return sorted(list(symbols))
            
        except Exception as e:
            logger.error(f"Error getting all stock symbols: {str(e)}")
            return []
    
    async def get_stock_history(self, symbol: str, days: int = 30) -> List[Dict]:
        """Get historical data for a stock"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            history = []
            current = start_date
            while current <= end_date:
                date_str = current.strftime("%Y-%m-%d")
                filename = f"{date_str}_{symbol}.json"
                filepath = self.data_dir / "stocks" / filename
                
                if filepath.exists():
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        history.append(data)
                
                current += timedelta(days=1)
            
            return sorted(history, key=lambda x: x['date'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting stock history for {symbol}: {str(e)}")
            return []
    
    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")
            
            # Clean up old stock data
            stock_files = list(self.data_dir.glob("stocks/*.json"))
            removed_count = 0
            
            for file in stock_files:
                try:
                    # Extract date from filename
                    date_str = file.stem.split('_')[0]
                    if date_str < cutoff_str:
                        file.unlink()
                        removed_count += 1
                except:
                    continue
            
            logger.info(f"Cleaned up {removed_count} old stock data files")
            
            # Clean up old reports (keep more reports than stock data)
            report_cutoff = datetime.now() - timedelta(days=days_to_keep * 2)
            report_cutoff_str = report_cutoff.strftime("%Y-%m-%d")
            
            report_files = list(self.data_dir.glob("reports/*.json"))
            removed_reports = 0
            
            for file in report_files:
                try:
                    # Extract date from report ID: DR_YYYY-MM-DD.json
                    if file.stem.startswith("DR_"):
                        date_str = file.stem[3:]  # Remove "DR_" prefix
                        if date_str < report_cutoff_str:
                            file.unlink()
                            removed_reports += 1
                except:
                    continue
            
            logger.info(f"Cleaned up {removed_reports} old report files")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stock_files = list(self.data_dir.glob("stocks/*.json"))
            report_files = list(self.data_dir.glob("reports/*.json"))
            summary_files = list(self.data_dir.glob("summaries/*.json"))
            
            # Calculate total size
            total_size = 0
            for file_list in [stock_files, report_files, summary_files]:
                for file in file_list:
                    total_size += file.stat().st_size
            
            # Get date range of data
            if stock_files:
                dates = []
                for file in stock_files:
                    try:
                        date_str = file.stem.split('_')[0]
                        dates.append(date_str)
                    except:
                        continue
                dates.sort()
                earliest_date = dates[0] if dates else None
                latest_date = dates[-1] if dates else None
            else:
                earliest_date = latest_date = None
            
            return {
                "total_files": len(stock_files) + len(report_files) + len(summary_files),
                "stock_data_files": len(stock_files),
                "daily_reports": len(report_files),
                "summary_reports": len(summary_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "earliest_date": earliest_date,
                "latest_date": latest_date,
                "unique_symbols": len(await self.get_all_stock_symbols())
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get storage health status"""
        try:
            # Check if directories exist and are writable
            directories_ok = all([
                self.data_dir.exists(),
                (self.data_dir / "stocks").exists(),
                (self.data_dir / "reports").exists(),
                (self.data_dir / "summaries").exists(),
            ])
            
            # Check write permissions
            test_file = self.data_dir / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                writable = True
            except:
                writable = False
            
            status = "healthy" if directories_ok and writable else "error"
            
            return {
                "status": status,
                "directories_exist": directories_ok,
                "writable": writable,
                "data_directory": str(self.data_dir),
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }