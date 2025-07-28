# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an automated stock analysis trading bot system designed to:
- Collect daily stock market data at 12:00 Kyiv time
- Analyze data using LLM (OpenAI GPT-4 or Claude via llm7.io)
- Generate daily investment recommendations for two categories:
  - **Stable investments**: $200 (80%) - large cap stocks, ETFs, dividend aristocrats
  - **Risky investments**: $50 (20%) - growth stocks, small/mid cap, leveraged ETFs
- Create daily and 30-day summary reports
- Provide REST API access to recommendations and reports

## Architecture

The system follows this data flow:
```
Data Sources → Data Collector → OpenSearch → AI Processor → Report Generator
```

### Key Components:
- **Backend**: Python 3.11+ with FastAPI
- **Database**: OpenSearch for data storage and search
- **Cache**: Redis for API response caching
- **Task Scheduler**: Celery with Redis broker
- **LLM**: OpenAI GPT-4 or Claude (via llm7.io)
- **Deployment**: Docker + Docker Compose

### Data Sources:
- Yahoo Finance (via yfinance) - real-time prices, historical data
- Alpha Vantage - technical indicators, fundamentals (5 requests/min free)
- Financial Modeling Prep - financial reports (250 requests/day free)
- News APIs - financial news and sentiment

## Project Structure

```
trading_bot/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── models/
│   │   ├── stock_data.py      # Pydantic models for stock data
│   │   └── reports.py         # Report models
│   ├── services/
│   │   ├── data_collector.py  # Data collection from APIs
│   │   ├── analyzer.py        # LLM analysis service
│   │   ├── opensearch_client.py # OpenSearch operations
│   │   └── report_generator.py # Report generation
│   ├── api/
│   │   ├── stocks.py          # Stock-related endpoints
│   │   └── reports.py         # Report endpoints
│   └── tasks/
│       ├── daily_tasks.py     # Celery tasks for daily analysis
│       └── scheduler.py       # Cron scheduling configuration
├── docker compose.yml         # Multi-service deployment
├── Dockerfile                 # Container configuration
└── requirements.txt           # Python dependencies
```

## Stock Watchlist

### Stable Assets (20 positions):
- **Large Cap Tech**: AAPL, MSFT, GOOGL, AMZN, META
- **ETF Funds**: SPY, QQQ, VTI, VOO, SCHD
- **Blue Chips**: JNJ, PG, KO, WMT, HD
- **Financial**: JPM, BAC, BRK-B, V, MA

### Risky Assets (15 positions):
- **Growth Tech**: NVDA, TSLA, PLTR, SNOW, ZM
- **Small/Mid Cap**: UPST, ROKU, DKNG, COIN
- **Leverage ETF**: TQQQ, SOXL, ARKK, SPXL, TECL

## Development Commands

Since this project is in early planning stages, the following commands are expected based on the architecture:

```bash
# Development setup
docker compose up -d                    # Start all services
docker compose logs -f app              # View application logs
docker compose logs -f celery           # View task worker logs

# Manual task execution
python -m app.tasks.daily_tasks         # Run daily analysis manually
python -m app.services.data_collector   # Test data collection

# API testing
curl http://localhost:8000/api/v1/recommendations/current
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/reports/daily/2025-07-29

# Database operations
curl http://localhost:9200/_cluster/health  # OpenSearch health
curl http://localhost:9200/_cat/indices     # View OpenSearch indices
```

## Key Data Models

### Stock Data Structure:
- **Price data**: OHLCV + previous close, change percentage
- **Technical indicators**: RSI, MACD, SMA (20/50/200), Bollinger Bands
- **Fundamental metrics**: P/E ratio, market cap, dividend yield, EPS, revenue growth
- **Sentiment data**: News sentiment score, analyst ratings, social sentiment

### AI Analysis Output:
- **Trend direction**: BULLISH/BEARISH/SIDEWAYS with strength score
- **Risk assessment**: Risk score (0-1), volatility forecast
- **Recommendation**: BUY/HOLD/SELL with confidence level
- **Price targets**: 7-day and 30-day predictions
- **Key factors**: List of reasoning points

## Scheduled Tasks

- **Daily Analysis**: 09:00 UTC (12:00 Kyiv) - collect data, analyze, generate daily report
- **Summary Reports**: Weekly on Mondays at 10:00 UTC - generate 30-day summary

## Important Notes

- All stock symbols should be validated against the predefined watchlist
- API keys must be stored in environment variables, never in code
- The system processes 35+ stocks within 15 minutes during daily analysis
- Recommendations are categorized as either STABLE or RISKY based on analysis
- All reports and analyses are stored in OpenSearch with time-series indexing
- The system is designed for Ukrainian timezone (Kyiv) with UTC conversion for scheduling

## Environment Variables

```bash
OPENSEARCH_HOST=opensearch
REDIS_HOST=redis
OPENAI_API_KEY=your_openai_key
ALPHA_VANTAGE_KEY=your_alpha_vantage_key
NEWS_API_KEY=your_news_api_key
```

This system serves as a foundation for automated investment analysis with room for future enhancements like backtesting, machine learning models, and portfolio management features.
