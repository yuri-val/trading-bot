# Детальна інструкція для AI агента: Розробка бота аналізу акцій

> **ПРИМІТКА**: Цей документ містить застарілі посилання на OpenSearch та старі моделі LLM. 
> Для актуальної інформації про проект використовуйте `CLAUDE.md` у кореневій папці.
> Поточна система використовує JSON-зберігання та GPT-5-nano через llm7.io.

## 1. Огляд системи

### Цілі бота:
- Щоденний збір даних про акції та ринок
- Аналіз трендів та генерація інсайтів
- Створення щоденних звітів (Daily Reports)
- Генерація підсумкових звітів за 30 днів (Summary Reports)
- Рекомендації для двох категорій інвестицій: стабільні ($200) та ризикові ($50)

### Архітектура системи:
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   Data Collector │───▶│   JSON Storage  │
│ • Yahoo Finance │    │ • Stock Lists    │    │ • File System  │
│ • Alpha Vantage │    │ • Validators     │    │ • Structured    │
│ • News APIs     │    │ • Transformers   │    │ • Time-series   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐            │
│   Report Output │◀───│   LLM Analysis   │◀───────────┘
│ • Daily Reports │    │ • GPT-5-nano     │
│ • Summaries     │    │ • Pattern Recog. │
│ • API Results   │    │ • Recommendations│
└─────────────────┘    └──────────────────┘
```

## 2. Технічний стек

### Основні технології:
- **Backend**: Python 3.11+ з FastAPI
- **Storage**: JSON файли для структурованого зберігання даних
- **Cache/Broker**: Redis для Celery черги задач
- **LLM**: llm7.io GPT-5-nano (primary), OpenAI GPT-5-mini (fallback)
- **Scheduler**: Celery з Redis broker
- **Monitoring**: Prometheus + Grafana
- **Deployment**: Docker + Docker Compose

### Залежності Python:
```python
fastapi>=0.104.1
redis>=5.0.1
celery>=5.3.4
openai>=1.3.8
requests>=2.31.0
pandas>=2.1.3
numpy>=1.25.2
pydantic>=2.5.0
yfinance>=0.2.22
alpha-vantage>=2.3.1
beautifulsoup4>=4.12.2
aiohttp>=3.8.0
pydantic-settings>=2.0.0
```

## 3. Джерела даних

### Безкоштовні API:
1. **Yahoo Finance** (через yfinance)
   - Ціни акцій в реальному часі
   - Історичні дані
   - Фінансові показники компаній

2. **Alpha Vantage** (безкоштовно до 5 запитів/хв)
   - Технічні індикатори
   - Фундаментальні дані
   - Новини

3. **Ландинг партнери** (опціонально)
   - Financial Modeling Prep
   - Twelve Data
   - IEX Cloud

4. **News API** або **NewsData.io**
   - Фінансові новини
   - Настрої ринку

### Структура збираних даних:
```python
# Stock Data Model
{
    "symbol": "AAPL",
    "date": "2025-07-29",
    "price_data": {
        "open": 150.25,
        "high": 152.10,
        "low": 149.80,
        "close": 151.75,
        "volume": 45000000,
        "adj_close": 151.75
    },
    "technical_indicators": {
        "rsi": 65.5,
        "macd": 2.1,
        "sma_20": 148.30,
        "sma_50": 145.60,
        "bollinger_upper": 155.20,
        "bollinger_lower": 142.40
    },
    "fundamental_data": {
        "pe_ratio": 28.5,
        "market_cap": 2400000000000,
        "dividend_yield": 0.52,
        "eps": 5.32
    },
    "sentiment": {
        "news_sentiment": 0.65,
        "social_sentiment": 0.42,
        "analyst_rating": "BUY"
    }
}
```

## 4. Структура зберігання даних (JSON)

### Організація файлів:
```
data/
├── stocks/                    # Щоденні дані акцій
│   ├── YYYY-MM-DD_SYMBOL.json
│   └── ...
├── reports/                   # Щоденні звіти
│   ├── DR_YYYY-MM-DD.json
│   └── ...
├── summaries/                 # Підсумкові звіти
│   ├── SR_YYYY-MM-DD.json
│   └── MR_YYYY-MM-DD.json    # Місячні звіти
└── stock_lists.json          # Поточні списки акцій
```

### Структура файлу акції:
```json
{
  "symbol": "AAPL",
  "date": "2025-08-18",
  "category": "STABLE",
  "price_data": {
    "open": 150.25,
    "high": 152.10,
    "low": 149.80,
    "close": 151.75,
    "volume": 45000000,
    "previous_close": 149.50,
    "change_percent": 1.50
  },
  "technical_indicators": {
    "rsi": 65.5,
    "macd": 2.1,
    "sma_20": 148.30,
    "sma_50": 145.60,
    "bollinger_upper": 155.20,
    "bollinger_lower": 142.40
  },
  "ai_analysis": {
    "recommendation": "BUY",
    "confidence": 0.85,
    "trend_direction": "BULLISH",
    "risk_score": 0.3,
    "reasoning": "Сильні фундаментальні показники та позитивний технічний тренд",
    "price_target_30d": 165.00
  },
  "metadata": {
    "analysis_timestamp": "2025-08-18T09:15:00Z",
    "llm_model": "gpt-5-nano-2025-08-07",
    "data_sources": ["yfinance", "alpha_vantage"]
  }
}
```

## 5. Структура проекту

```
trading_bot/
├── app/
│   ├── main.py                      # FastAPI застосунок з health checks
│   ├── config.py                    # Динамічна конфігурація
│   ├── models/
│   │   ├── stock_data.py           # Pydantic моделі для даних акцій
│   │   └── reports.py              # Моделі звітів та рекомендацій
│   ├── services/
│   │   ├── stock_list_collector.py # Динамічний збір списків акцій
│   │   ├── data_collector.py       # Мульти-джерельний збір даних
│   │   ├── analyzer.py             # LLM аналіз (GPT-5-nano)
│   │   ├── json_storage.py         # JSON файлове зберігання
│   │   ├── llm_adapter.py          # Адаптер для багатьох LLM провайдерів
│   │   └── report_generator.py     # Генерація щоденних/підсумкових звітів
│   ├── api/
│   │   ├── stocks.py               # Ендпойнти для аналізу акцій та watchlist
│   │   └── reports.py              # Ендпойнти для звітів та рекомендацій
│   └── tasks/
│       ├── daily_tasks.py          # Celery задачі для автоматизованого аналізу
│       └── scheduler.py            # Конфігурація cron планування
├── data/                           # JSON зберігання
│   ├── stocks/                     # Щоденні дані аналізу акцій
│   ├── reports/                    # Щоденні звіти
│   ├── summaries/                  # 30-денні підсумкові звіти
│   └── stock_lists.json           # Поточні динамічні списки акцій
├── docs/                           # Документація
├── docker-compose.yml              # Redis + app сервіси
├── Dockerfile                      # Конфігурація контейнера
├── requirements.txt                # Python залежності
└── run.py                         # Скрипт управління для розробки
```

## 6. Ключові компоненти

### 6.1 Data Collector (app/services/data_collector.py)

```python
import yfinance as yf
import requests
from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, timedelta

class DataCollector:
    def __init__(self):
        self.av_key = "YOUR_ALPHA_VANTAGE_KEY"
        self.ts = TimeSeries(key=self.av_key, output_format='pandas')

    async def collect_stock_data(self, symbols: list):
        """Збирає дані по списку акцій"""
        data = {}
        for symbol in symbols:
            ticker = yf.Ticker(symbol)

            # Основні дані
            hist = ticker.history(period="5d")
            info = ticker.info

            # Технічні індикатори через Alpha Vantage
            tech_data = self.get_technical_indicators(symbol)

            # Новини та настрої
            news_sentiment = await self.get_news_sentiment(symbol)

            data[symbol] = {
                "symbol": symbol,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "price_data": {
                    "open": float(hist['Open'].iloc[-1]),
                    "high": float(hist['High'].iloc[-1]),
                    "low": float(hist['Low'].iloc[-1]),
                    "close": float(hist['Close'].iloc[-1]),
                    "volume": int(hist['Volume'].iloc[-1])
                },
                "fundamental_data": {
                    "pe_ratio": info.get('forwardPE'),
                    "market_cap": info.get('marketCap'),
                    "dividend_yield": info.get('dividendYield')
                },
                "technical_indicators": tech_data,
                "sentiment": news_sentiment
            }

        return data

    def get_watchlist(self):
        """Повертає список акцій для моніторингу"""
        stable_stocks = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "SPY", "QQQ", "VTI", "BRK-A", "JNJ"
        ]

        risky_stocks = [
            "TSLA", "PLTR", "RIVN", "COIN", "ROKU",
            "ARKK", "SOXL", "TQQQ", "UPST", "ZM"
        ]

        return {
            "stable": stable_stocks,
            "risky": risky_stocks
        }
```

### 6.2 LLM Analyzer (app/services/analyzer.py)

```python
import openai
from typing import Dict, List
import json

class LLMAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    async def analyze_stock_data(self, stock_data: Dict) -> Dict:
        """Аналізує дані акції через LLM"""

        prompt = f"""
        Ти - експерт з фінансового аналізу. Проаналізуй наступні дані акції {stock_data['symbol']}:

        Ціна: {stock_data['price_data']}
        Технічні індикатори: {stock_data['technical_indicators']}
        Фундаментальні дані: {stock_data['fundamental_data']}
        Настрої: {stock_data['sentiment']}

        Дай відповідь у JSON форматі:
        {{
            "trend_direction": "BULLISH/BEARISH/SIDEWAYS",
            "risk_score": 0.0-1.0,
            "recommendation": "BUY/HOLD/SELL",
            "confidence": 0.0-1.0,
            "key_factors": ["фактор1", "фактор2"],
            "price_target_30d": число,
            "category": "STABLE/RISKY"
        }}
        """

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        try:
            analysis = json.loads(response.choices[0].message.content)
            return analysis
        except json.JSONDecodeError:
            return self.fallback_analysis(stock_data)

    async def generate_daily_report(self, all_stock_data: List[Dict]) -> str:
        """Генерує щоденний звіт"""

        stable_picks = []
        risky_picks = []

        for stock in all_stock_data:
            if stock['ai_analysis']['category'] == 'STABLE' and stock['ai_analysis']['recommendation'] == 'BUY':
                stable_picks.append(stock)
            elif stock['ai_analysis']['category'] == 'RISKY' and stock['ai_analysis']['recommendation'] == 'BUY':
                risky_picks.append(stock)

        # Сортуємо за confidence score
        stable_picks.sort(key=lambda x: x['ai_analysis']['confidence'], reverse=True)
        risky_picks.sort(key=lambda x: x['ai_analysis']['confidence'], reverse=True)

        report_prompt = f"""
        Створи щоденний інвестиційний звіт на основі аналізу {len(all_stock_data)} акцій.

        ТОП стабільні позиції: {stable_picks[:3]}
        ТОП ризикові позиції: {risky_picks[:3]}

        Структура звіту:
        1. Короткий огляд ринку
        2. Рекомендація для стабільної позиції ($200)
        3. Рекомендація для ризикової позиції ($50)
        4. Ключові ризики та можливості
        5. Технічний та фундаментальний аналіз

        Звіт має бути конкретним та дієвим.
        """

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": report_prompt}],
            temperature=0.5
        )

        return response.choices[0].message.content
```

### 6.3 Daily Task (app/tasks/daily_tasks.py)

```python
from celery import Celery
from datetime import datetime
import asyncio

celery_app = Celery('trading_bot')

@celery_app.task
def daily_analysis_task():
    """Щоденна задача аналізу - запускається о 12:00 Київ"""

    async def run_analysis():
        # Ініціалізація сервісів
        collector = DataCollector()
        analyzer = LLMAnalyzer(api_key="your_openai_key")
        opensearch = OpenSearchClient()
        report_gen = ReportGenerator()

        # Отримуємо список акцій
        watchlist = collector.get_watchlist()
        all_symbols = watchlist['stable'] + watchlist['risky']

        # Збираємо дані
        print(f"[{datetime.now()}] Збираю дані для {len(all_symbols)} акцій...")
        stock_data = await collector.collect_stock_data(all_symbols)

        # Аналізуємо через LLM
        analyzed_data = []
        for symbol, data in stock_data.items():
            print(f"Аналізую {symbol}...")
            analysis = await analyzer.analyze_stock_data(data)
            data['ai_analysis'] = analysis
            analyzed_data.append(data)

        # Зберігаємо в OpenSearch
        today = datetime.now().strftime("%Y-%m-%d")
        index_name = f"daily-stock-data-{datetime.now().strftime('%Y-%m')}"

        for data in analyzed_data:
            await opensearch.index_document(index_name, data)

        # Генеруємо щоденний звіт
        daily_report = await analyzer.generate_daily_report(analyzed_data)

        # Зберігаємо звіт
        report_data = {
            "date": today,
            "report_type": "daily",
            "content": daily_report,
            "analyzed_stocks_count": len(analyzed_data),
            "top_stable_pick": analyzed_data[0]['symbol'] if analyzed_data else None,
            "top_risky_pick": analyzed_data[-1]['symbol'] if analyzed_data else None
        }

        report_index = f"daily-reports-{datetime.now().strftime('%Y-%m')}"
        await opensearch.index_document(report_index, report_data)

        print(f"[{datetime.now()}] Щоденний аналіз завершено!")
        return daily_report

    # Запускаємо async функцію
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(run_analysis())

@celery_app.task
def generate_summary_report():
    """Генерує summary звіт за останні 30 днів"""

    async def run_summary():
        opensearch = OpenSearchClient()
        analyzer = LLMAnalyzer(api_key="your_openai_key")

        # Отримуємо щоденні звіти за 30 днів
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        daily_reports = await opensearch.search_reports(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )

        # Аналізуємо тренди
        summary_prompt = f"""
        Проаналізуй {len(daily_reports)} щоденних звітів за останні 30 днів.

        Звіти: {daily_reports}

        Створи summary звіт з:
        1. Загальним трендом ринку за місяць
        2. Найкращими стабільними позиціями (ТОП-3)
        3. Найкращими ризиковими позиціями (ТОП-3)
        4. Ключовими інсайтами та змінами в настроях
        5. Рекомендаціями на наступний місяць

        Включи статистику: успішність прогнозів, ROI, волатильність.
        """

        response = await analyzer.client.chat.completions.create(
            model=analyzer.model,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.3
        )

        summary_report = response.choices[0].message.content

        # Зберігаємо summary звіт
        summary_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "report_type": "summary_30d",
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "content": summary_report,
            "daily_reports_analyzed": len(daily_reports)
        }

        summary_index = f"summary-reports-{datetime.now().strftime('%Y')}"
        await opensearch.index_document(summary_index, summary_data)

        return summary_report

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(run_summary())
```

## 7. API Endpoints

### 7.1 Основні endpoints (app/api/reports.py)

```python
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/daily-report/{date}")
async def get_daily_report(date: str):
    """Отримати щоденний звіт за конкретну дату"""
    opensearch = OpenSearchClient()

    try:
        report = await opensearch.get_daily_report(date)
        return report
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Звіт не знайдено: {str(e)}")

@router.get("/summary-report")
async def get_summary_report(days: int = 30):
    """Генерувати summary звіт за останні N днів"""

    # Запускаємо задачу генерації
    task = generate_summary_report.delay()

    return {
        "message": "Summary звіт генерується...",
        "task_id": task.id,
        "status": "processing"
    }

@router.get("/recommendations/current")
async def get_current_recommendations():
    """Отримати поточні рекомендації"""
    opensearch = OpenSearchClient()

    # Отримуємо останній щоденний звіт
    today = datetime.now().strftime("%Y-%m-%d")
    report = await opensearch.get_daily_report(today)

    if not report:
        # Якщо немає звіту за сьогодні, беремо останній доступний
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        report = await opensearch.get_daily_report(yesterday)

    return {
        "date": report.get("date"),
        "stable_recommendation": report.get("top_stable_pick"),
        "risky_recommendation": report.get("top_risky_pick"),
        "investment_amounts": {
            "stable": 200,
            "risky": 50
        }
    }

@router.get("/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    """Отримати аналіз конкретної акції"""
    opensearch = OpenSearchClient()

    # Отримуємо останні дані по акції
    stock_data = await opensearch.get_latest_stock_data(symbol)

    return stock_data
```

## 8. Конфігурація та деплой

### 8.1 Docker Compose (docker compose.yml)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENSEARCH_HOST=opensearch
      - REDIS_HOST=trade_bot-redis
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - opensearch
      - redis
    volumes:
      - ./app:/app

  celery:
    build: .
    command: celery -A app.tasks.daily_tasks worker --loglevel=info
    environment:
      - OPENSEARCH_HOST=opensearch
      - REDIS_HOST=trade_bot-redis
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
      - opensearch

  celery-beat:
    build: .
    command: celery -A app.tasks.daily_tasks beat --loglevel=info
    environment:
      - OPENSEARCH_HOST=opensearch
      - REDIS_HOST=trade_bot-redis
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis

  opensearch:
    image: opensearchproject/opensearch:2.11.0
    environment:
      - discovery.type=single-node
      - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
      - "DISABLE_SECURITY_PLUGIN=true"
    ports:
      - "9200:9200"
    volumes:
      - opensearch_data:/usr/share/opensearch/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  opensearch_data:
```

### 8.2 Cron налаштування

```python
# app/tasks/scheduler.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'daily-analysis': {
        'task': 'app.tasks.daily_tasks.daily_analysis_task',
        'schedule': crontab(hour=9, minute=0),  # 12:00 Київ = 09:00 UTC
    },
    'weekly-summary': {
        'task': 'app.tasks.daily_tasks.generate_summary_report',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Понеділок 13:00 Київ
    },
}

celery_app.conf.timezone = 'UTC'
```

## 9. Запуск та тестування

### 9.1 Команди для запуску:

```bash
# Клонування та налаштування
git clone <your_repo>
cd trading_bot

# Налаштування середовища
cp .env.example .env
# Заповнити API ключі в .env файлі

# Запуск через Docker
docker compose up -d

# Перевірка логів
docker compose logs -f app
docker compose logs -f celery

# Тестовий запуск аналізу
curl http://localhost:8000/recommendations/current
```

### 9.2 Моніторинг:

```bash
# Перевірка стану Redis
curl http://localhost:6380 || echo "Redis is accessible on port 6380"

# Перевірка контейнерів Docker
docker compose ps

# API статус
curl http://localhost:8000/health

# Flower monitoring
curl http://localhost:5555
```

## 10. Розширення та оптимізація

### Подальші вдосконалення:
1. **Бектестинг** - тестування стратегій на історичних даних
2. **Machine Learning** - додавання ML моделей для прогнозування
3. **Sentiment Analysis** - більш глибокий аналіз настроїв
4. **Portfolio Management** - відстеження реального портфеля
5. **Risk Management** - автоматичні стоп-лосси та тейк-профіти
6. **Telegram Bot** - сповіщення та команди через Telegram
7. **Web Dashboard** - веб-інтерфейс для перегляду аналітики

### Метрики для відстеження:
- Точність прогнозів
- ROI по рекомендаціях
- Sharpe ratio
- Maximum drawdown
- Успішність категоризації (stable vs risky)

Ця система створить потужний фундамент для автоматизованого аналізу акцій з можливістю масштабування та вдосконалення!
