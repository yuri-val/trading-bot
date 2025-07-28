# Trading Bot - Automated Stock Analysis System

An automated stock analysis and investment recommendation system that provides daily analysis and investment suggestions for both stable ($200) and risky ($50) investment strategies.

## Features

- **Dynamic Stock Lists**: Daily collection of stable and risky stocks from internet sources
- **Daily Stock Analysis**: Automated collection and analysis of 40+ stocks
- **LLM-Powered Insights**: Uses OpenAI GPT-4-1-nano for intelligent market analysis
- **Dual Investment Strategy**: Recommendations for stable ($200) and risky ($50) allocations
- **Real-time Data**: Integration with Yahoo Finance, Alpha Vantage, and news APIs
- **Comprehensive Reports**: Daily and 30-day summary reports
- **REST API**: Full API access to all data and recommendations
- **Scheduled Analysis**: Automatic daily analysis at 12:00 Kyiv time
- **Lightweight Storage**: JSON file-based storage system for efficient data management

## Architecture

```
Stock Collector → Data Collector → JSON Storage → AI Processor → Report Generator
     ↓                ↓              ↓             ↓            ↓
Web Scraping     Yahoo Finance   File System   LLM Analysis   Daily Reports
S&P 500 Lists    Alpha Vantage   Structured    Risk Scoring   API Endpoints
Dividend Stocks  News APIs       JSON Files    Confidence     Web Interface
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- API Keys:
  - OpenAI API key (for GPT-4-1-nano)
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

# Start Redis service
docker compose up redis -d

# Create data directory
mkdir -p data

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

### Dynamic Stock Collection

**Stable Stocks (up to 25 positions)**:
- S&P 500 top companies by market cap
- Dividend Aristocrats (25+ years of dividend increases)
- Popular ETFs: SPY, QQQ, VTI, VOO, SCHD
- Blue chip companies: AAPL, MSFT, JNJ, JPM, PG, KO, WMT, HD, V, MA

**Risky Stocks (up to 15 positions)**:
- Daily top gainers and most active stocks
- Growth ETF holdings
- High-beta volatile stocks: TSLA, NVDA, AMD, NFLX
- Leveraged ETFs: TQQQ, SOXL, ARKK, SPXL, TECL
- Recent IPOs and SPACs

*Stock lists are automatically updated daily from internet sources*

### Scheduled Tasks

- **Daily Analysis**: 09:00 UTC (12:00 Kyiv) - Monday to Friday
- **Weekly Summary**: 10:00 UTC Monday (13:00 Kyiv) - Last 30 days
- **Health Monitoring**: Every hour

## Data Flow

1. **Stock List Update** (09:00 UTC)
   - Web scraping of S&P 500, dividend aristocrats, top gainers
   - Dynamic collection of stable and risky stock candidates
   - Validation of stock liquidity and tradability

2. **Data Collection** (09:05 UTC)
   - Yahoo Finance: Price data, historical trends for updated lists
   - Alpha Vantage: Technical indicators, fundamentals
   - News APIs: Sentiment analysis, market news

3. **AI Analysis** (09:10-09:35 UTC)
   - LLM processes each stock individually using GPT-4-1-nano
   - Generates trend analysis, risk scores, recommendations
   - Assigns confidence levels and price targets

4. **Report Generation** (09:35-09:40 UTC)
   - Creates daily investment report
   - Selects best stable and risky recommendations
   - Stores all data in JSON files

5. **API Availability** (09:40+ UTC)
   - Fresh recommendations available via API
   - Historical data accessible through JSON storage

## Monitoring

### Health Checks

```bash
# System health
curl http://localhost:8000/health

# System status with storage stats
curl http://localhost:8000/api/v1/status

# Redis connectivity
docker exec trade-bot_redis_1 redis-cli ping

# Celery workers
curl http://localhost:5555/api/workers

# Check data directory
ls -la data/
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
# JSON data backup
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# Redis persistence
docker exec redis_container redis-cli BGSAVE

# Stock lists backup
cp data/stock_lists.json stock_lists_backup_$(date +%Y%m%d).json
```

## Troubleshooting

### Common Issues

1. **API Rate Limits**
   - Alpha Vantage: 5 requests/min (free tier)
   - Solution: Implement request queuing or upgrade plan

2. **JSON Storage Issues**
   - Check data directory permissions
   - Monitor disk space usage

3. **Celery Tasks Failing**
   - Check Redis connectivity
   - Verify API keys are set correctly
   - Review worker logs for specific errors
   - Ensure data directory is writable

### Debug Commands

```bash
# Test data collection with dynamic stock lists
python -c "from app.services.data_collector import DataCollector; import asyncio; dc = DataCollector(); print(asyncio.run(dc.collect_daily_data()))"

# Test JSON storage
python -c "from app.services.json_storage import JSONStorage; js = JSONStorage(); print(js.get_health_status())"

# Test stock list collection
python -c "from app.services.stock_list_collector import StockListCollector; import asyncio; slc = StockListCollector(); print(asyncio.run(slc.update_stock_lists()))"

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

## Recent Updates

### v2.0 - Dynamic Stock Collection
- **Dynamic Stock Lists**: Stock lists are now collected daily from internet sources instead of using static lists
- **Improved Coverage**: Up to 25 stable stocks and 15 risky stocks based on real-time market data
- **Lightweight Architecture**: Replaced OpenSearch with JSON file storage for better performance and simplicity
- **Enhanced Reliability**: Improved data validation and fallback mechanisms
- **Better Monitoring**: Enhanced health checks and system status reporting

## Disclaimer

This system provides automated analysis and suggestions for educational and informational purposes only. It is not financial advice. Always conduct your own research and consider consulting with qualified financial advisors before making investment decisions. Past performance does not guarantee future results.
