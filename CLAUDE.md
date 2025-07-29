# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an automated stock analysis trading bot system designed to:
- **Dynamically collect stock lists** daily from internet sources (S&P 500, dividend aristocrats, top gainers)
- **Analyze 40+ stocks** daily at 12:00 Kyiv time using GPT-4-1-nano
- **Generate investment recommendations** for two categories:
  - **Stable investments**: $200 (80%) - up to 25 large cap stocks, ETFs, dividend aristocrats
  - **Risky investments**: $50 (20%) - up to 15 growth stocks, leveraged ETFs, recent IPOs
- **Create daily and 30-day summary reports** with AI-generated insights
- **Provide REST API access** to all recommendations, reports, and stock data

## Architecture

The system follows this modernized data flow:
```
Stock Collector → Data Collector → JSON Storage → AI Processor → Report Generator
     ↓                ↓              ↓             ↓            ↓
Web Scraping     Yahoo Finance   File System   LLM Analysis   Daily Reports
S&P 500 Lists    Alpha Vantage   Structured    Risk Scoring   API Endpoints
Dividend Stocks  News APIs       JSON Files    Confidence     Web Interface
```

### Key Components:
- **Backend**: Python 3.11+ with FastAPI
- **Storage**: JSON file-based storage system (replaced OpenSearch for simplicity)
- **Cache/Broker**: Redis for Celery task queue
- **Task Scheduler**: Celery with Redis broker for daily analysis
- **LLM**: OpenAI GPT-4-1-nano for stock analysis
- **Deployment**: Docker + Docker Compose

### Data Sources:
- **Web Scraping**: Wikipedia S&P 500, dividend aristocrats lists
- **Yahoo Finance** (via yfinance): Real-time prices, historical data, top gainers
- **Alpha Vantage**: Technical indicators, fundamentals (5 requests/min free tier)
- **News APIs**: Financial news sentiment analysis

## Project Structure

```
trading_bot/
├── app/
│   ├── main.py                      # FastAPI application with health checks
│   ├── config.py                    # Dynamic configuration (no static stock lists)
│   ├── models/
│   │   ├── stock_data.py           # Pydantic models for stock data and analysis
│   │   └── reports.py              # Report and recommendation models
│   ├── services/
│   │   ├── stock_list_collector.py # Dynamic stock list collection from web
│   │   ├── data_collector.py       # Multi-source data collection
│   │   ├── analyzer.py             # LLM analysis service (GPT-4-1-nano)
│   │   ├── json_storage.py         # JSON file storage operations
│   │   └── report_generator.py     # Daily/summary report generation
│   ├── api/
│   │   ├── stocks.py               # Stock analysis and watchlist endpoints
│   │   └── reports.py              # Report and recommendation endpoints
│   └── tasks/
│       ├── daily_tasks.py          # Celery tasks for automated analysis
│       └── scheduler.py            # Cron scheduling configuration
├── data/                           # JSON storage directory
│   ├── stocks/                     # Daily stock analysis data
│   ├── reports/                    # Daily reports
│   ├── summaries/                  # 30-day summary reports
│   └── stock_lists.json           # Current dynamic stock lists
├── docker-compose.yml              # Redis + app services (OpenSearch removed)
├── Dockerfile                      # Container configuration
└── requirements.txt                # Python dependencies
```

## Development Commands

### Docker Operations
```bash
# Start all services (app, celery worker, celery beat, redis)
docker compose up -d

# View logs
docker compose logs -f app              # Application logs
docker compose logs -f celery-worker    # Task worker logs
docker compose logs -f celery-beat      # Scheduler logs

# Individual service management
docker compose up redis -d              # Start only Redis
docker compose restart app              # Restart main application
```

### Local Development
```bash
# Start Redis only
docker compose up redis -d

# Run application locally
export OPENAI_API_KEY="your-key"
export ALPHA_VANTAGE_KEY="your-key"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (separate terminal)
celery -A app.tasks.daily_tasks worker --loglevel=info

# Run Celery beat scheduler (separate terminal)
celery -A app.tasks.daily_tasks beat --loglevel=info
```

### Manual Task Execution
```bash
# Trigger daily analysis manually
python -m app.tasks.daily_tasks daily

# Generate 30-day summary report
python -m app.tasks.daily_tasks summary

# Test individual components
python -c "from app.services.stock_list_collector import StockListCollector; import asyncio; slc = StockListCollector(); print(asyncio.run(slc.update_stock_lists()))"

python -c "from app.services.data_collector import DataCollector; import asyncio; dc = DataCollector(); print(asyncio.run(dc.collect_daily_data()))"
```

### API Testing
```bash
# System health and status
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/status

# Current recommendations
curl http://localhost:8000/api/v1/reports/current-recommendations

# Dynamic watchlist
curl http://localhost:8000/api/v1/stocks/watchlist

# Individual stock analysis
curl http://localhost:8000/api/v1/stocks/AAPL/analysis
curl http://localhost:8000/api/v1/stocks/AAPL/recommendation

# Daily reports
curl http://localhost:8000/api/v1/reports/daily/latest
curl http://localhost:8000/api/v1/reports/daily/2025-07-28
```

### Storage Operations
```bash
# Check data directory structure
ls -la data/stocks/     # Daily stock data files
ls -la data/reports/    # Daily reports
ls -la data/summaries/  # 30-day summary reports

# View current stock lists
cat data/stock_lists.json

# Storage statistics
curl http://localhost:8000/api/v1/status | jq '.storage_stats'
```

## Dynamic Stock Collection

The system automatically updates stock lists daily by collecting from multiple internet sources:

### Stable Stock Sources (up to 25):
- **S&P 500 Top Companies**: Scraped from Wikipedia, sorted by market cap
- **Dividend Aristocrats**: Companies with 25+ years of dividend increases
- **Popular ETFs**: SPY, QQQ, VTI, VOO, SCHD, IVV, VEA, IEFA, VWO
- **Blue Chip Fallbacks**: AAPL, MSFT, JNJ, JPM, PG, KO, WMT, HD, V, MA, UNH, DIS

### Risky Stock Sources (up to 15):
- **Daily Top Gainers**: Scraped from Yahoo Finance screener
- **Growth ETF Holdings**: Common growth stocks from popular growth ETFs
- **High-Beta Stocks**: TSLA, NVDA, AMD, NFLX, ZOOM, PLTR, COIN, UPST, ROKU, DKNG
- **Leveraged ETFs**: TQQQ, SOXL, ARKK, SPXL, TECL, UPRO, TNA
- **Recent IPOs**: COIN, UPST, RBLX, PLTR, SNOW, CRWD, ZM, DOCU, PTON, RIVN, LCID, HOOD, SOFI, AFRM

## Key Data Models

### StockData Structure:
- **Basic Info**: symbol, date, category (STABLE/RISKY)
- **Price Data**: OHLCV, previous close, change percentage
- **Technical Indicators**: RSI-14, MACD, SMA-20/50, Bollinger Bands
- **Fundamental Data**: P/E ratio, market cap, dividend yield, EPS, revenue growth, debt-to-equity
- **Sentiment Data**: News sentiment score, article count, social sentiment, analyst rating
- **AI Analysis**: Recommendation (BUY/HOLD/SELL), confidence level, reasoning, risk score, price targets

### Report Models:
- **DailyReport**: Market overview, stable/risky recommendations, risks, processing metrics
- **SummaryReport**: 30-day performance analysis, top performers, market trends, insights, outlook
- **CurrentRecommendations**: Today's investment suggestions with allocations and reasoning

## Scheduled Tasks (Celery Beat)

- **Daily Analysis**: 09:00 UTC (12:00 Kyiv) Monday-Friday
  1. Update stock lists from internet sources
  2. Collect data for all stocks
  3. Run LLM analysis on each stock
  4. Generate daily investment report
  5. Save all data to JSON storage

- **Weekly Summary**: 10:00 UTC Monday (13:00 Kyiv)
  - Generate 30-day summary report with performance analysis

## Important Architecture Notes

### Stock List Management:
- Stock lists are **dynamic and updated daily** from internet sources
- No static lists in configuration - all managed by `StockListCollector`
- Stocks are validated for liquidity (minimum 100,000 daily volume)
- Fallback lists exist if internet collection fails

### Storage System:
- **JSON files** replace OpenSearch for simplicity and performance
- Data organized by date: `data/stocks/YYYY-MM-DD_SYMBOL.json`
- Reports stored as: `data/reports/DR_YYYY-MM-DD.json`
- Automatic cleanup of old data (configurable retention period)

### LLM Integration:
- Uses **GPT-4-1-nano** model for cost efficiency
- Each stock analyzed individually with comprehensive prompts
- Analysis includes trend direction, risk assessment, price targets, and reasoning
- Confidence levels and recommendation categories guide report generation

### Data Flow:
1. **Stock Collection** (09:00 UTC): Web scraping and validation
2. **Data Gathering** (09:05 UTC): Multi-source API calls
3. **AI Analysis** (09:10-09:35 UTC): Individual stock analysis
4. **Report Generation** (09:35-09:40 UTC): Daily report with recommendations
5. **API Availability** (09:40+ UTC): Fresh data accessible via REST API

## Environment Variables

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key
ALPHA_VANTAGE_KEY=your_alpha_vantage_key

# Optional
NEWS_API_KEY=your_news_api_key

# Service Configuration
REDIS_HOST=trade_bot-redis
REDIS_PORT=6379
```

## Configuration Settings

Key settings in `app/config.py`:
- `max_stable_stocks: 25` - Maximum stable stocks to collect
- `max_risky_stocks: 15` - Maximum risky stocks to collect
- `stable_investment: 200` - Dollar allocation for stable recommendations
- `risky_investment: 50` - Dollar allocation for risky recommendations
- `confidence_threshold: 0.6` - Minimum confidence for BUY recommendations
- `stock_validation_volume_threshold: 100000` - Minimum daily volume for stock validation

This system represents a modern, lightweight approach to automated investment analysis with dynamic data collection and efficient JSON-based storage.
