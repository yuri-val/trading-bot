# Trading Bot - Automated Stock Analysis System

An automated stock analysis and investment recommendation system that provides daily analysis and investment suggestions for both stable ($200) and risky ($50) investment strategies.

## Features

- **Daily Stock Analysis**: Automated collection and analysis of 35+ stocks
- **LLM-Powered Insights**: Uses OpenAI GPT-4 for intelligent market analysis
- **Dual Investment Strategy**: Recommendations for stable ($200) and risky ($50) allocations
- **Real-time Data**: Integration with Yahoo Finance, Alpha Vantage, and news APIs
- **Comprehensive Reports**: Daily and 30-day summary reports
- **REST API**: Full API access to all data and recommendations
- **Scheduled Analysis**: Automatic daily analysis at 12:00 Kyiv time

## Architecture

```
Data Sources → Data Collector → OpenSearch → AI Processor → Report Generator
     ↓              ↓              ↓           ↓            ↓
Yahoo Finance   Celery Tasks   Time-series   LLM Analysis   Daily Reports
Alpha Vantage   Scheduling     Full-text     Risk Scoring   API Endpoints
News APIs       Error Handling  Indexing      Confidence     Web Interface
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- API Keys:
  - OpenAI API key
  - Alpha Vantage API key (free tier: 5 requests/min)
  - News API key (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd trade-bot
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Start the system**
```bash
docker compose up -d
```

4. **Verify the installation**
```bash
curl http://localhost:8000/health
```

### API Documentation

Once running, visit:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Celery Monitoring**: http://localhost:5555
- **Data Visualization**: http://localhost:5601

## API Endpoints

### Core Endpoints

- `GET /` - API information
- `GET /health` - System health check
- `GET /api/v1/config` - System configuration

### Stock Analysis

- `GET /api/v1/stocks/{symbol}/analysis` - Detailed stock analysis
- `GET /api/v1/stocks/{symbol}/recommendation` - AI recommendation
- `GET /api/v1/stocks/watchlist` - Complete stock watchlist
- `GET /api/v1/stocks/trending` - Trending stocks by price movement

### Reports

- `GET /api/v1/reports/current-recommendations` - Current investment recommendations
- `GET /api/v1/reports/daily/{date}` - Daily report for specific date
- `GET /api/v1/reports/daily/latest` - Most recent daily report
- `POST /api/v1/reports/summary` - Generate 30-day summary report

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start services (OpenSearch + Redis)
docker compose up opensearch redis -d

# Set environment variables
export OPENAI_API_KEY="your-key"
export ALPHA_VANTAGE_KEY="your-key"

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (separate terminal)
celery -A app.tasks.daily_tasks worker --loglevel=info

# Run Celery beat scheduler (separate terminal)
celery -A app.tasks.daily_tasks beat --loglevel=info
```

### Manual Task Execution

```bash
# Run daily analysis manually
python -m app.tasks.daily_tasks daily

# Generate summary report
python -m app.tasks.daily_tasks summary

# Test Celery connectivity
python -m app.tasks.daily_tasks test
```

## Configuration

### Stock Watchlist

**Stable Stocks (20 positions)**:
- Large Cap Tech: AAPL, MSFT, GOOGL, AMZN, NVDA
- ETF Funds: SPY, QQQ, VTI, VOO, SCHD
- Blue Chips: JNJ, PG, KO, WMT, HD
- Financial: JPM, BAC, BRK-B, V, MA

**Risky Stocks (15 positions)**:
- Growth Tech: NVDA, TSLA, PLTR, SNOW, ZM
- Small/Mid Cap: UPST, ROKU, DKNG, COIN
- Leverage ETF: TQQQ, SOXL, ARKK, SPXL, TECL

### Scheduled Tasks

- **Daily Analysis**: 09:00 UTC (12:00 Kyiv) - Monday to Friday
- **Weekly Summary**: 10:00 UTC Monday (13:00 Kyiv) - Last 30 days
- **Health Monitoring**: Every hour

## Data Flow

1. **Data Collection** (09:00 UTC)
   - Yahoo Finance: Price data, historical trends
   - Alpha Vantage: Technical indicators, fundamentals
   - News APIs: Sentiment analysis, market news

2. **AI Analysis** (09:05-09:35 UTC)
   - LLM processes each stock individually
   - Generates trend analysis, risk scores, recommendations
   - Assigns confidence levels and price targets

3. **Report Generation** (09:35-09:40 UTC)
   - Creates daily investment report
   - Selects best stable and risky recommendations
   - Stores all data in OpenSearch

4. **API Availability** (09:40+ UTC)
   - Fresh recommendations available via API
   - Historical data searchable and accessible

## Monitoring

### Health Checks

```bash
# System health
curl http://localhost:8000/health

# OpenSearch status
curl http://localhost:9201/_cluster/health

# Redis connectivity
docker exec trade-bot_redis_1 redis-cli ping

# Celery workers
curl http://localhost:5555/api/workers
```

### Logs

```bash
# Application logs
docker compose logs -f app

# Celery worker logs
docker compose logs -f celery-worker

# All services
docker compose logs -f
```

## Production Deployment

### Security Considerations

1. **API Keys**: Use secure environment variable management
2. **Network**: Configure firewall rules for port access
3. **Authentication**: Add API authentication for production use
4. **SSL/TLS**: Use reverse proxy with SSL certificates
5. **Resource Limits**: Set appropriate memory and CPU limits

### Scaling

- **Horizontal**: Add more Celery workers for parallel processing
- **Vertical**: Increase memory/CPU for OpenSearch and Redis
- **Geographic**: Deploy in multiple regions for redundancy

### Backup Strategy

```bash
# OpenSearch data backup
docker exec opensearch_container curl -X POST "localhost:9200/_snapshot/backup"

# Redis persistence
docker exec redis_container redis-cli BGSAVE
```

## Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Alpha Vantage: 5 requests/min (free tier)
   - Solution: Implement request queuing or upgrade plan

2. **OpenSearch Memory**
   - Increase `OPENSEARCH_JAVA_OPTS` heap size
   - Monitor cluster health regularly

3. **Celery Tasks Failing**
   - Check Redis connectivity
   - Verify API keys are set correctly
   - Review worker logs for specific errors

### Debug Commands

```bash
# Test data collection
python -c "from app.services.data_collector import DataCollector; import asyncio; dc = DataCollector(); print(asyncio.run(dc.collect_stock_data(['AAPL'])))"

# Test OpenSearch connection
python -c "from app.services.opensearch_client import OpenSearchClient; import asyncio; osc = OpenSearchClient(); print(asyncio.run(osc.get_health_status()))"

# Test LLM analysis
python -c "from app.services.analyzer import LLMAnalyzer; print('Analyzer initialized successfully')"
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This system provides automated analysis and suggestions for educational and informational purposes only. It is not financial advice. Always conduct your own research and consider consulting with qualified financial advisors before making investment decisions. Past performance does not guarantee future results.
