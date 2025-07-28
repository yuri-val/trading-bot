import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import NotFoundError, RequestError

from ..config import settings
from ..models.stock_data import StockData
from ..models.reports import DailyReport, SummaryReport

logger = logging.getLogger(__name__)


class OpenSearchClient:
    def __init__(self):
        self.client = OpenSearch(
            hosts=[{
                'host': settings.opensearch_host,
                'port': settings.opensearch_port
            }],
            http_compress=True,
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            connection_class=RequestsHttpConnection
        )
        self._wait_for_connection()
        self._ensure_indices()
    
    def _wait_for_connection(self):
        """Wait for OpenSearch to be available"""
        import time
        max_retries = 30
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                health = self.client.cluster.health(timeout=5)
                logger.info(f"OpenSearch connected successfully: {health.get('status', 'unknown')}")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.info(f"Waiting for OpenSearch... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logger.warning(f"Could not connect to OpenSearch after {max_retries} attempts: {str(e)}")
                    break
    
    def _ensure_indices(self):
        """Create indices if they don't exist"""
        current_month = datetime.now().strftime("%Y-%m")
        current_year = datetime.now().strftime("%Y")
        
        indices = [
            f"daily-stock-data-{current_month}",
            f"market-news-{current_month}",
            f"daily-reports-{current_month}",
            f"summary-reports-{current_year}"
        ]
        
        for index_name in indices:
            try:
                if not self.client.indices.exists(index=index_name):
                    self._create_index(index_name)
                    logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.error(f"Error creating index {index_name}: {str(e)}")
    
    def _create_index(self, index_name: str):
        """Create index with appropriate mapping"""
        if "stock-data" in index_name:
            mapping = self._get_stock_data_mapping()
        elif "reports" in index_name:
            mapping = self._get_reports_mapping()
        else:
            mapping = {"mappings": {"properties": {}}}
        
        self.client.indices.create(index=index_name, body=mapping)
    
    def _get_stock_data_mapping(self) -> Dict:
        """Get mapping for stock data index"""
        return {
            "mappings": {
                "properties": {
                    "symbol": {"type": "keyword"},
                    "date": {"type": "date"},
                    "category": {"type": "keyword"},
                    "price_data": {
                        "properties": {
                            "open": {"type": "float"},
                            "high": {"type": "float"},
                            "low": {"type": "float"},
                            "close": {"type": "float"},
                            "volume": {"type": "long"},
                            "previous_close": {"type": "float"},
                            "change_percent": {"type": "float"}
                        }
                    },
                    "technical_indicators": {
                        "properties": {
                            "rsi_14": {"type": "float"},
                            "macd": {"type": "float"},
                            "macd_signal": {"type": "float"},
                            "sma_20": {"type": "float"},
                            "sma_50": {"type": "float"},
                            "sma_200": {"type": "float"},
                            "bollinger_upper": {"type": "float"},
                            "bollinger_lower": {"type": "float"}
                        }
                    },
                    "fundamental_data": {
                        "properties": {
                            "pe_ratio": {"type": "float"},
                            "market_cap": {"type": "long"},
                            "dividend_yield": {"type": "float"},
                            "eps_ttm": {"type": "float"},
                            "revenue_growth": {"type": "float"},
                            "debt_to_equity": {"type": "float"}
                        }
                    },
                    "ai_analysis": {
                        "properties": {
                            "trend_direction": {"type": "keyword"},
                            "trend_strength": {"type": "float"},
                            "risk_score": {"type": "float"},
                            "recommendation": {"type": "keyword"},
                            "confidence_level": {"type": "float"},
                            "target_allocation": {"type": "keyword"},
                            "price_target_7d": {"type": "float"},
                            "price_target_30d": {"type": "float"},
                            "key_factors": {"type": "text"},
                            "reasoning": {"type": "text"}
                        }
                    }
                }
            }
        }
    
    def _get_reports_mapping(self) -> Dict:
        """Get mapping for reports index"""
        return {
            "mappings": {
                "properties": {
                    "report_id": {"type": "keyword"},
                    "date": {"type": "date"},
                    "report_type": {"type": "keyword"},
                    "content": {"type": "text"},
                    "analyzed_stocks_count": {"type": "integer"},
                    "processing_time_minutes": {"type": "float"},
                    "stable_recommendation": {
                        "properties": {
                            "symbol": {"type": "keyword"},
                            "allocation": {"type": "integer"},
                            "confidence": {"type": "float"},
                            "reasoning": {"type": "text"}
                        }
                    },
                    "risky_recommendation": {
                        "properties": {
                            "symbol": {"type": "keyword"},
                            "allocation": {"type": "integer"},
                            "confidence": {"type": "float"},
                            "reasoning": {"type": "text"}
                        }
                    }
                }
            }
        }
    
    async def index_stock_data(self, stock_data: StockData) -> bool:
        """Index stock data"""
        try:
            index_name = f"daily-stock-data-{stock_data.date.strftime('%Y-%m')}"
            doc_id = f"{stock_data.symbol}-{stock_data.date.strftime('%Y-%m-%d')}"
            
            # Convert to dict and handle datetime serialization
            doc = stock_data.model_dump()
            doc['date'] = stock_data.date.isoformat()
            
            response = self.client.index(
                index=index_name,
                id=doc_id,
                body=doc
            )
            
            logger.info(f"Indexed stock data for {stock_data.symbol}: {response['result']}")
            return response['result'] in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Error indexing stock data for {stock_data.symbol}: {str(e)}")
            return False
    
    async def index_daily_report(self, report: DailyReport) -> bool:
        """Index daily report"""
        try:
            index_name = f"daily-reports-{report.date.strftime('%Y-%m')}"
            doc_id = report.report_id
            
            # Convert to dict and handle datetime serialization
            doc = report.model_dump()
            doc['date'] = report.date.isoformat()
            doc['market_overview']['date'] = report.market_overview.date.isoformat()
            
            response = self.client.index(
                index=index_name,
                id=doc_id,
                body=doc
            )
            
            logger.info(f"Indexed daily report: {response['result']}")
            return response['result'] in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Error indexing daily report: {str(e)}")
            return False
    
    async def index_summary_report(self, report: SummaryReport) -> bool:
        """Index summary report"""
        try:
            index_name = f"summary-reports-{report.start_date.strftime('%Y')}"
            doc_id = report.report_id
            
            # Convert to dict and handle datetime serialization
            doc = report.model_dump()
            doc['start_date'] = report.start_date.isoformat()
            doc['end_date'] = report.end_date.isoformat()
            
            response = self.client.index(
                index=index_name,
                id=doc_id,
                body=doc
            )
            
            logger.info(f"Indexed summary report: {response['result']}")
            return response['result'] in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Error indexing summary report: {str(e)}")
            return False
    
    async def get_latest_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get latest stock data for a symbol"""
        try:
            # Search in current month's index
            index_name = f"daily-stock-data-{datetime.now().strftime('%Y-%m')}"
            
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"symbol": symbol}}
                        ]
                    }
                },
                "sort": [
                    {"date": {"order": "desc"}}
                ],
                "size": 1
            }
            
            response = self.client.search(index=index_name, body=query)
            
            if response['hits']['total']['value'] > 0:
                return response['hits']['hits'][0]['_source']
            else:
                return None
                
        except NotFoundError:
            logger.warning(f"Index not found for latest stock data: {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error getting latest stock data for {symbol}: {str(e)}")
            return None
    
    async def get_daily_report(self, date: str) -> Optional[Dict]:
        """Get daily report for a specific date"""
        try:
            # Parse date to get the correct index
            report_date = datetime.strptime(date, "%Y-%m-%d")
            index_name = f"daily-reports-{report_date.strftime('%Y-%m')}"
            doc_id = f"DR_{date}"
            
            response = self.client.get(index=index_name, id=doc_id)
            return response['_source']
            
        except NotFoundError:
            logger.warning(f"Daily report not found for date: {date}")
            return None
        except Exception as e:
            logger.error(f"Error getting daily report for {date}: {str(e)}")
            return None
    
    async def search_reports(self, start_date: str, end_date: str, report_type: str = "DAILY") -> List[Dict]:
        """Search for reports within date range"""
        try:
            # Determine which indices to search
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            indices = []
            current = start.replace(day=1)
            while current <= end:
                if report_type == "DAILY":
                    indices.append(f"daily-reports-{current.strftime('%Y-%m')}")
                else:
                    indices.append(f"summary-reports-{current.strftime('%Y')}")
                
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"report_type": report_type}},
                            {"range": {
                                "date": {
                                    "gte": start_date,
                                    "lte": end_date
                                }
                            }}
                        ]
                    }
                },
                "sort": [
                    {"date": {"order": "desc"}}
                ],
                "size": 100
            }
            
            # Remove non-existent indices
            existing_indices = [idx for idx in indices if self.client.indices.exists(index=idx)]
            
            if not existing_indices:
                return []
            
            response = self.client.search(index=existing_indices, body=query)
            
            return [hit['_source'] for hit in response['hits']['hits']]
            
        except Exception as e:
            logger.error(f"Error searching reports: {str(e)}")
            return []
    
    async def get_health_status(self) -> Dict:
        """Get OpenSearch cluster health"""
        try:
            health = self.client.cluster.health()
            return {
                "status": health.get("status", "unknown"),
                "number_of_nodes": health.get("number_of_nodes", 0),
                "active_primary_shards": health.get("active_primary_shards", 0),
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting health status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }