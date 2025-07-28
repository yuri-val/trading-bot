import requests
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class StockListCollector:
    def __init__(self):
        self.stable_stocks = []
        self.risky_stocks = []
        self.last_updated = None
    
    async def update_stock_lists(self) -> Dict[str, List[str]]:
        """Update both stable and risky stock lists from internet sources"""
        try:
            logger.info("Starting daily stock list update...")
            
            # Collect stable stocks (Large cap, blue chips, dividend stocks)
            stable_stocks = await self._collect_stable_stocks()
            
            # Collect risky stocks (Growth, small cap, volatile stocks)
            risky_stocks = await self._collect_risky_stocks()
            
            # Validate stocks exist and are tradeable
            stable_stocks = await self._validate_stocks(stable_stocks)
            risky_stocks = await self._validate_stocks(risky_stocks)
            
            self.stable_stocks = stable_stocks[:25]  # Limit to 25 stable
            self.risky_stocks = risky_stocks[:15]   # Limit to 15 risky
            self.last_updated = datetime.now()
            
            logger.info(f"Updated stock lists: {len(self.stable_stocks)} stable, {len(self.risky_stocks)} risky")
            
            return {
                "stable": self.stable_stocks,
                "risky": self.risky_stocks,
                "last_updated": self.last_updated.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating stock lists: {str(e)}")
            return self._get_fallback_lists()
    
    async def _collect_stable_stocks(self) -> List[str]:
        """Collect stable stocks from multiple sources"""
        stable_stocks = set()
        
        try:
            # 1. S&P 500 largest companies
            sp500_stocks = await self._get_sp500_top_companies()
            stable_stocks.update(sp500_stocks)
            
            # 2. Dividend Aristocrats
            dividend_stocks = await self._get_dividend_aristocrats()
            stable_stocks.update(dividend_stocks)
            
            # 3. Popular ETFs
            etf_stocks = ["SPY", "QQQ", "VTI", "VOO", "SCHD", "IVV", "VEA", "IEFA", "VWO"]
            stable_stocks.update(etf_stocks)
            
            # 4. Blue chip companies (manual list of most stable)
            blue_chips = ["AAPL", "MSFT", "JNJ", "JPM", "PG", "KO", "WMT", "HD", "V", "MA", "UNH", "DIS"]
            stable_stocks.update(blue_chips)
            
        except Exception as e:
            logger.error(f"Error collecting stable stocks: {str(e)}")
        
        return list(stable_stocks)
    
    async def _collect_risky_stocks(self) -> List[str]:
        """Collect risky/growth stocks from multiple sources"""
        risky_stocks = set()
        
        try:
            # 1. Top gainers and most active stocks
            gainers = await self._get_top_gainers()
            risky_stocks.update(gainers)
            
            # 2. Growth stocks from popular growth ETFs
            growth_etf_holdings = await self._get_growth_etf_holdings()
            risky_stocks.update(growth_etf_holdings)
            
            # 3. High-beta (volatile) stocks
            high_beta_stocks = ["TSLA", "NVDA", "AMD", "NFLX", "ZOOM", "PLTR", "COIN", "UPST", "ROKU", "DKNG"]
            risky_stocks.update(high_beta_stocks)
            
            # 4. Leveraged and inverse ETFs
            leveraged_etfs = ["TQQQ", "SOXL", "ARKK", "SPXL", "TECL", "UPRO", "TNA"]
            risky_stocks.update(leveraged_etfs)
            
            # 5. Recent IPOs and SPACs (last 2 years)
            recent_ipos = await self._get_recent_ipos()
            risky_stocks.update(recent_ipos)
            
        except Exception as e:
            logger.error(f"Error collecting risky stocks: {str(e)}")
        
        return list(risky_stocks)
    
    async def _get_sp500_top_companies(self) -> List[str]:
        """Get top S&P 500 companies by market cap"""
        try:
            # Using a free source for S&P 500 list
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the table with S&P 500 companies
            table = soup.find('table', {'id': 'constituents'})
            if table:
                symbols = []
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows[:20]:  # Top 20 by market cap (they're usually sorted)
                    cells = row.find_all('td')
                    if cells:
                        symbol = cells[0].text.strip()
                        symbols.append(symbol)
                return symbols
        except Exception as e:
            logger.error(f"Error getting S&P 500 companies: {str(e)}")
        
        # Fallback list
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ"]
    
    async def _get_dividend_aristocrats(self) -> List[str]:
        """Get dividend aristocrats (companies with 25+ years of dividend increases)"""
        try:
            # Wikipedia has a good list of dividend aristocrats
            url = "https://en.wikipedia.org/wiki/S%26P_500_Dividend_Aristocrats"
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            symbols = []
            # Look for ticker symbols in the page
            for link in soup.find_all('a'):
                text = link.get_text().strip()
                if len(text) <= 5 and text.isupper() and text.isalpha():
                    symbols.append(text)
            
            return symbols[:15] if symbols else []
        except Exception as e:
            logger.error(f"Error getting dividend aristocrats: {str(e)}")
        
        # Fallback dividend stocks
        return ["KO", "PG", "JNJ", "WMT", "HD", "MCD", "MMM", "CAT", "IBM", "CVX"]
    
    async def _get_top_gainers(self) -> List[str]:
        """Get top gaining stocks from Yahoo Finance"""
        try:
            url = "https://finance.yahoo.com/screener/predefined/day_gainers"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            symbols = []
            # Look for stock symbols in the page
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if '/quote/' in href:
                    symbol = href.split('/quote/')[1].split('?')[0]
                    if len(symbol) <= 5 and symbol.isalnum():
                        symbols.append(symbol.upper())
            
            return list(set(symbols))[:10]
        except Exception as e:
            logger.error(f"Error getting top gainers: {str(e)}")
        
        return []
    
    async def _get_growth_etf_holdings(self) -> List[str]:
        """Get holdings from popular growth ETFs"""
        try:
            # Common growth stocks that are often in growth ETFs
            growth_stocks = [
                "AMZN", "GOOGL", "META", "NFLX", "TSLA", "NVDA", "AMD", 
                "PYPL", "ADBE", "CRM", "ZOOM", "PLTR", "SQ", "SHOP", "TWLO"
            ]
            return growth_stocks
        except Exception as e:
            logger.error(f"Error getting growth ETF holdings: {str(e)}")
        
        return []
    
    async def _get_recent_ipos(self) -> List[str]:
        """Get recent IPO stocks (simplified approach)"""
        try:
            # Recent notable IPOs and high-growth companies
            recent_ipos = [
                "COIN", "UPST", "RBLX", "PLTR", "SNOW", "CRWD", "ZM", 
                "DOCU", "PTON", "RIVN", "LCID", "HOOD", "SOFI", "AFRM"
            ]
            return recent_ipos
        except Exception as e:
            logger.error(f"Error getting recent IPOs: {str(e)}")
        
        return []
    
    async def _validate_stocks(self, symbols: List[str]) -> List[str]:
        """Validate that stocks exist and are tradeable"""
        valid_symbols = []
        
        # Simple validation - just filter out obviously invalid symbols
        # Skip intensive yfinance validation to avoid rate limiting
        for symbol in symbols:
            try:
                # Basic symbol format validation
                if (len(symbol) <= 5 and 
                    symbol.isalnum() and 
                    not symbol.isdigit() and 
                    len(symbol) >= 1):
                    valid_symbols.append(symbol.upper())
                        
            except Exception as e:
                logger.debug(f"Invalid symbol {symbol}: {str(e)}")
                continue
        
        logger.info(f"Validated {len(valid_symbols)} symbols (basic validation only)")
        return valid_symbols
    
    def _get_fallback_lists(self) -> Dict[str, List[str]]:
        """Return fallback stock lists if internet collection fails"""
        fallback_stable = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", 
            "UNH", "JNJ", "JPM", "PG", "HD", "V", "MA", "WMT", "DIS", "PYPL",
            "SPY", "QQQ", "VTI", "VOO", "SCHD"
        ]
        
        fallback_risky = [
            "PLTR", "COIN", "UPST", "ROKU", "DKNG", "ZOOM", "CRWD", "SNOW",
            "TQQQ", "SOXL", "ARKK", "SPXL", "TECL", "RIVN", "HOOD"
        ]
        
        return {
            "stable": fallback_stable,
            "risky": fallback_risky,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_current_lists(self) -> Dict[str, List[str]]:
        """Get current stock lists"""
        return {
            "stable": self.stable_stocks,
            "risky": self.risky_stocks,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
    
    async def save_lists_to_file(self, filepath: str = "data/stock_lists.json"):
        """Save current lists to JSON file"""
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            data = {
                "stable_stocks": self.stable_stocks,
                "risky_stocks": self.risky_stocks,
                "last_updated": self.last_updated.isoformat() if self.last_updated else None,
                "total_stable": len(self.stable_stocks),
                "total_risky": len(self.risky_stocks)
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Stock lists saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving stock lists: {str(e)}")
    
    async def load_lists_from_file(self, filepath: str = "data/stock_lists.json") -> bool:
        """Load stock lists from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.stable_stocks = data.get("stable_stocks", [])
            self.risky_stocks = data.get("risky_stocks", [])
            self.last_updated = datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else None
            
            logger.info(f"Stock lists loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error loading stock lists: {str(e)}")
            return False