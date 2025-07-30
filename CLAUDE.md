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
- **LLM**: llm7.io with gpt-4.1-nano-2025-04-14 (primary), OpenAI GPT-4 (fallback)
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
python run.py analysis                    # Alternative using run script
python run.py analysis --docker          # Using Docker container

# Generate 30-day summary report
python -m app.tasks.daily_tasks summary
python run.py summary                     # Alternative using run script
python run.py summary --days 7           # Custom number of days

# Test individual components
python -c "from app.services.stock_list_collector import StockListCollector; import asyncio; slc = StockListCollector(); print(asyncio.run(slc.update_stock_lists()))"

python -c "from app.services.data_collector import DataCollector; import asyncio; dc = DataCollector(); print(asyncio.run(dc.collect_daily_data()))"
```

### Development & Testing Commands
```bash
# System management using run.py script
python run.py docker                      # Start all services with Docker
python run.py stop                        # Stop Docker services
python run.py health                      # Check system health
python run.py status                      # Show detailed system status
python run.py containers                  # Show container status
python run.py tasks                       # Check task execution status
python run.py logs                        # View all service logs

# Individual service management
python run.py api                         # Run FastAPI server locally
python run.py worker                      # Run Celery worker locally
python run.py beat                        # Run Celery beat scheduler locally
python run.py flower                      # Run Flower monitoring interface

# Docker container testing
python run.py worker --docker             # Run worker in Docker container
python run.py beat --docker               # Run beat scheduler in Docker
python run.py flower --docker             # Run Flower in Docker

# Direct dependency installation
pip install -r requirements.txt

# Test core services individually
python -c "from app.config import settings; print(f'Config loaded: {settings.max_stable_stocks} stable stocks')"
python -c "from app.services.json_storage import JSONStorage; js = JSONStorage(); print(js.get_health_status())"

# Test LLM providers
curl http://localhost:8000/api/v1/llm/test
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
- **Primary Provider**: llm7.io with **gpt-4.1-nano-2025-04-14** model for cost efficiency and performance
- **Fallback Provider**: OpenAI with GPT-4 for reliability
- **Multi-provider architecture** ensures high availability with automatic failover
- Each stock analyzed individually with comprehensive prompts
- Analysis includes trend direction, risk assessment, price targets, and reasoning
- Confidence levels and recommendation categories guide report generation
- **Test endpoint**: `/api/v1/llm/test` for provider connectivity verification

### Data Flow:
1. **Stock Collection** (09:00 UTC): Web scraping and validation
2. **Data Gathering** (09:05 UTC): Multi-source API calls
3. **AI Analysis** (09:10-09:35 UTC): Individual stock analysis
4. **Report Generation** (09:35-09:40 UTC): Daily report with recommendations
5. **API Availability** (09:40+ UTC): Fresh data accessible via REST API

## Environment Variables

```bash
# LLM API Keys (Primary: llm7.io, Fallback: OpenAI)
LLM7_API_KEY=your_llm7_api_key          # Primary LLM provider (llm7.io)
OPENAI_API_KEY=your_openai_api_key      # Fallback LLM provider

# Data Source API Keys
ALPHA_VANTAGE_KEY=your_alpha_vantage_key

# Optional API Keys  
NEWS_API_KEY=your_news_api_key
TWELVE_DATA_API_KEY=your_twelve_data_key
IEX_TOKEN=your_iex_token
FMP_API_KEY=your_financial_modeling_prep_key

# Service Configuration
REDIS_HOST=trade_bot-redis  # Use localhost for local development
REDIS_PORT=6379
REDIS_DB=0

# Application Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

### Environment Setup
```bash
# Copy example environment file
cp .env.example .env

# Edit with your API keys
nano .env  # or your preferred editor

# Verify configuration
python -c "from app.config import settings; print('Config loaded successfully')"
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

## Development Workflow

### Daily Development Tasks
1. **System Status Check**: `python run.py health` - Check all services
2. **View Current Data**: `python run.py status` - See analysis status and configuration  
3. **Manual Analysis**: `python run.py analysis` - Trigger analysis for testing
4. **Check Results**: `python run.py tasks` - Verify task completion and file creation
5. **Monitor Services**: `python run.py logs` - Watch service logs in real-time

### Code Architecture Understanding
- **Entry Point**: `app/main.py` - FastAPI application with health checks and API routes
- **Configuration**: `app/config.py` - Centralized settings using Pydantic BaseSettings
- **Models**: `app/models/` - Pydantic data models for stock data and reports  
- **Services**: `app/services/` - Core business logic (data collection, analysis, storage)
- **API Routes**: `app/api/` - REST endpoints for stocks and reports
- **Background Tasks**: `app/tasks/` - Celery tasks for scheduled analysis
- **Utility Script**: `run.py` - Management script for all development operations

### Key Service Dependencies
- **Stock List Collector** → **Data Collector** → **LLM Analyzer** → **Report Generator** → **JSON Storage**
- Each service is designed to be testable independently
- JSON storage provides simple file-based persistence without external database dependencies
- Celery + Redis handle background processing and scheduling
