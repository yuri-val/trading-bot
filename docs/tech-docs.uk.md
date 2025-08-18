# Технічне завдання: Система автоматизованого аналізу акцій

> **ПРИМІТКА**: Цей документ містить застарілі технічні специфікації. 
> Для актуальної інформації про проект використовуйте `CLAUDE.md` у кореневій папці.
> Поточна система використовує JSON-зберігання та GPT-5-nano через llm7.io.

## 1. Мета та завдання проекту

### 1.1 Бізнес-цілі
Створити автоматизовану систему для щоденного аналізу фондового ринку, яка допомагатиме приватному інвестору приймати обґрунтовані рішення щодо інвестицій у розмірі $250 на місяць.

### 1.2 Основні завдання
- Щоденний збір та аналіз ринкових даних
- Генерація AI-рекомендацій для двох типів інвестицій
- Ведення історії аналізів та звітності
- Створення підсумкових звітів за періоди

### 1.3 Цільова аудиторія
Приватні інвестори з бюджетом $200-300 на місяць, які шукають баланс між стабільними та ризиковими інвестиціями.

## 2. Функціональні вимоги

### 2.1 Основний функціонал

#### F1: Збір ринкових даних
- **Щоденний збір** даних о 12:00 за київським часом
- **Джерела даних**: Yahoo Finance, Alpha Vantage, Financial Modeling Prep, News API
- **Типи даних**: ціни акцій, технічні індикатори, фундаментальні показники, новини
- **Охоплення**: мінімум 20 стабільних та 15 ризикових активів

#### F2: AI-аналіз даних
- **LLM обробка** всіх зібраних даних через OpenAI API або llm7.io
- **Категоризація** активів: стабільні vs ризикові
- **Генерація рекомендацій**: BUY/HOLD/SELL з рівнем довіри
- **Прогнозування** цінових цілей на 30 днів

#### F3: Звітність
- **Щоденні звіти** з конкретними рекомендаціями
- **Summary звіти** за останні 30 днів за запитом
- **Історичне зберігання** всіх звітів та аналізів
- **Метрики ефективності** прогнозів

#### F4: API інтерфейс
- **RESTful API** для отримання рекомендацій
- **Ендпойнти** для звітів, аналізу окремих акцій
- **Статус моніторинг** системи

### 2.2 Інвестиційна стратегія

#### Розподіл капіталу:
- **$200 (80%)** - стабільні активи з низьким ризиком
- **$50 (20%)** - високоризикові активи з потенціалом x2-x3

#### Критерії стабільних активів:
- Великі компанії (Large Cap) з ринковою капіталізацією $10B+
- ETF фонди (S&P 500, Nasdaq, сектораальні)
- Дивідендні аристократи
- P/E ratio < 30, стабільна історія прибутків

#### Критерії ризикових активів:
- Малі/середні компанії з високим потенціалом росту
- Технологічні стартапи після IPO
- Leverage ETF фонди
- Акції з високою волатильністю (>30% річна)

## 3. Технічні вимоги

### 3.1 Архітектура системи
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│Stock Collector  │───▶│   Data Collector │───▶│   JSON Storage  │
│• S&P 500 Lists  │    │• Yahoo Finance   │    │• File System    │
│• Dividend Stocks│    │• Alpha Vantage   │    │• Structured     │
│• Top Gainers    │    │• News APIs       │    │• Time-series    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐            │
│   Report Output │◀───│   LLM Processor  │◀───────────┘
│• Daily Reports  │    │• GPT-5-nano      │
│• Summary        │    │• Pattern Recog.  │
│• API Results    │    │• Recommendations │
└─────────────────┘    └──────────────────┘
```

### 3.2 Технологічний стек
- **Backend Framework**: Python FastAPI
- **Зберігання даних**: JSON файли для структурованого зберігання
- **Cache/Broker**: Redis для Celery черги задач
- **Task Queue**: Celery для асинхронних задач
- **AI/LLM**: llm7.io GPT-5-nano (primary), OpenAI GPT-5-mini (fallback)
- **Containerization**: Docker + Docker Compose
- **Monitoring**: Базові метрики та логування

### 3.3 Системні вимоги
- **Продуктивність**: обробка 40+ акцій за 25 хвилин (з урахуванням динамічного збору)
- **Доступність**: 99% uptime для API
- **Зберігання**: мінімум 1 рік історичних даних у JSON файлах
- **Безпека**: API ключі в environment variables, ніяких секретів у коді
- **Масштабованість**: динамічне додавання нових активів через інтернет-джерела

## 4. Структура даних

### 4.1 Модель даних для акцій
```json
{
  "stock_data": {
    "symbol": "AAPL",
    "date": "2025-07-29T12:00:00Z",
    "category": "STABLE|RISKY",
    "price_info": {
      "open": 150.25,
      "high": 152.10,
      "low": 149.80,
      "close": 151.75,
      "volume": 45000000,
      "previous_close": 150.00,
      "change_percent": 1.17
    },
    "technical_indicators": {
      "rsi_14": 65.5,
      "macd": 2.1,
      "macd_signal": 1.8,
      "sma_20": 148.30,
      "sma_50": 145.60,
      "sma_200": 140.20,
      "bollinger_upper": 155.20,
      "bollinger_lower": 142.40,
      "volume_sma": 42000000
    },
    "fundamental_metrics": {
      "pe_ratio": 28.5,
      "market_cap": 2400000000000,
      "dividend_yield": 0.52,
      "eps_ttm": 5.32,
      "revenue_growth": 0.08,
      "debt_to_equity": 1.73
    },
    "sentiment_data": {
      "news_sentiment_score": 0.65,
      "news_articles_count": 12,
      "social_sentiment": 0.42,
      "analyst_rating": "BUY",
      "analyst_price_target": 165.00
    }
  }
}
```

### 4.2 Модель AI аналізу
```json
{
  "ai_analysis": {
    "symbol": "AAPL",
    "analysis_date": "2025-07-29T12:15:00Z",
    "trend_analysis": {
      "direction": "BULLISH|BEARISH|SIDEWAYS",
      "strength": 0.75,
      "timeframe": "30_DAYS"
    },
    "risk_assessment": {
      "risk_score": 0.35,
      "risk_category": "LOW|MEDIUM|HIGH",
      "volatility_forecast": 0.25
    },
    "recommendation": {
      "action": "BUY|HOLD|SELL",
      "confidence_level": 0.82,
      "position_size": "FULL|PARTIAL|MINIMAL",
      "target_allocation": "STABLE|RISKY"
    },
    "price_predictions": {
      "target_7d": 154.20,
      "target_30d": 162.00,
      "support_level": 147.50,
      "resistance_level": 158.00
    },
    "key_factors": [
      "Strong earnings momentum",
      "Positive technical breakout",
      "Sector rotation favorability"
    ],
    "reasoning": "Короткий опис логіки рекомендації"
  }
}
```

### 4.3 Модель щоденного звіту
```json
{
  "daily_report": {
    "report_id": "DR_2025-07-29",
    "date": "2025-07-29",
    "report_type": "DAILY",
    "market_overview": {
      "market_sentiment": "POSITIVE",
      "major_indices": {
        "SP500_change": 0.75,
        "NASDAQ_change": 1.20,
        "VIX_level": 18.5
      },
      "market_themes": [
        "Tech sector strength",
        "Fed policy expectations",
        "Earnings season impact"
      ]
    },
    "recommendations": {
      "stable_pick": {
        "symbol": "AAPL",
        "allocation": 200,
        "reasoning": "Strong fundamentals with technical breakout",
        "confidence": 0.85,
        "expected_return_30d": 0.07
      },
      "risky_pick": {
        "symbol": "PLTR",
        "allocation": 50,
        "reasoning": "AI sector momentum with government contracts",
        "confidence": 0.72,
        "expected_return_30d": 0.25,
        "max_risk": 0.40
      }
    },
    "market_risks": [
      "Potential Fed policy shift",
      "Geopolitical tensions",
      "Sector rotation risks"
    ],
    "stats": {
      "analyzed_stocks": 35,
      "processing_time_minutes": 12,
      "data_quality_score": 0.94
    }
  }
}
```

### 4.4 Модель summary звіту
```json
{
  "summary_report": {
    "report_id": "SR_2025-07-29_30D",
    "period": {
      "start_date": "2025-06-29",
      "end_date": "2025-07-29",
      "days_analyzed": 30
    },
    "performance_metrics": {
      "total_recommendations": 60,
      "stable_picks_count": 30,
      "risky_picks_count": 30,
      "prediction_accuracy": 0.73,
      "avg_confidence_score": 0.78
    },
    "top_performers": {
      "stable_category": [
        {"symbol": "AAPL", "frequency": 8, "avg_return": 0.05},
        {"symbol": "MSFT", "frequency": 6, "avg_return": 0.04},
        {"symbol": "SPY", "frequency": 5, "avg_return": 0.03}
      ],
      "risky_category": [
        {"symbol": "NVDA", "frequency": 4, "avg_return": 0.15},
        {"symbol": "PLTR", "frequency": 3, "avg_return": 0.22},
        {"symbol": "COIN", "frequency": 2, "avg_return": 0.18}
      ]
    },
    "market_trends": {
      "dominant_themes": [
        "AI sector growth",
        "Interest rate sensitivity",
        "Earnings quality focus"
      ],
      "sector_performance": {
        "technology": 0.08,
        "healthcare": 0.03,
        "financial": 0.02
      }
    },
    "insights": [
      "Tech stocks showed consistent outperformance",
      "Risk assets demonstrated higher volatility",
      "Defensive positions provided stability"
    ],
    "next_month_outlook": "Модель прогнозу на наступний період"
  }
}
```

## 5. API специфікації

### 5.1 Ендпойнти

#### GET /api/v1/recommendations/current
Повертає поточні рекомендації для інвестування
**Response:**
```json
{
  "date": "2025-07-29",
  "stable_recommendation": {
    "symbol": "AAPL",
    "amount": 200,
    "confidence": 0.85,
    "reasoning": "Strong technical and fundamental signals"
  },
  "risky_recommendation": {
    "symbol": "PLTR",
    "amount": 50,
    "confidence": 0.72,
    "reasoning": "AI momentum with potential 2x returns"
  },
  "market_context": "Brief market overview"
}
```

#### GET /api/v1/reports/daily/{date}
Отримання щоденного звіту за конкретну дату

#### POST /api/v1/reports/summary
Генерація summary звіту за період
**Request:**
```json
{
  "start_date": "2025-06-29",
  "end_date": "2025-07-29",
  "format": "JSON|PDF"
}
```

#### GET /api/v1/stocks/{symbol}/analysis
Детальний аналіз конкретної акції

#### GET /api/v1/health
Статус системи та останнього аналізу

## 6. Бізнес-процеси

### 6.1 Щоденний workflow
```
09:00 UTC (12:00 Київ) - Початок збору даних
├── 09:00-09:05 - Збір цінових даних
├── 09:05-09:10 - Технічні індикатори
├── 09:10-09:15 - Фундаментальні дані
├── 09:15-09:20 - Новини та настрої
├── 09:20-09:35 - AI аналіз (35 акцій × 30 сек)
├── 09:35-09:40 - Генерація звіту
└── 09:40 - Збереження та публікація
```

### 6.2 Список активів для моніторингу

#### Стабільні активи (20 позицій):
- **Large Cap Tech**: AAPL, MSFT, GOOGL, AMZN, META
- **ETF Funds**: SPY, QQQ, VTI, VOO, SCHD
- **Blue Chips**: JNJ, PG, KO, WMT, HD
- **Financial**: JPM, BAC, BRK-B, V, MA

#### Ризикові активи (15 позицій):
- **Growth Tech**: NVDA, TSLA, PLTR, SNOW, ZM
- **Small/Mid Cap**: UPST, ROKU, DKNG, COIN
- **Leverage ETF**: TQQQ, SOXL, ARKK, SPXL, TECL

### 6.3 Критерії якості даних
- **Мінімальний обсяг торгів**: 1M акцій на день
- **Ліквідність**: bid-ask spread < 1%
- **Доступність даних**: всі технічні індикатори присутні
- **Новини**: мінімум 5 релевантних статей на тиждень

## 7. Критерії успіху та метрики

### 7.1 KPI системи
- **Точність прогнозів**: >70% правильних напрямків руху
- **Покрита прибутковість**: >8% річних для стабільних активів
- **Ризик-менеджмент**: максимальний drawdown <15% для ризикових
- **Система uptime**: >99% доступність API

### 7.2 Бізнес-метрики
- **ROI по рекомендаціях**: відстеження реальних результатів
- **Sharpe ratio**: >1.0 для комбінованого портфеля
- **Win rate**: >60% прибуткових рекомендацій
- **Average holding period**: оптимальний час утримання позицій

## 8. Ризики та обмеження

### 8.1 Технічні ризики
- **API лімити**: безкоштовні API мають обмеження запитів
- **Якість даних**: затримки або помилки в джерелах
- **LLM надійність**: потенційні помилки в AI аналізі
- **Інфраструктура**: збої серверів або мереж

### 8.2 Фінансові ризики
- **Ринкова волатильність**: непередбачувані рухи ринку
- **Системний ризик**: загальне падіння ринків
- **Модельний ризик**: помилки в алгоритмах аналізу
- **Ліквідність**: проблеми з виконанням операцій

### 8.3 Обмеження системи
- Не є інвестиційною порадою
- Потребує людського нагляду та валідації
- Ефективність залежить від ринкових умов
- Не гарантує прибутковість

## 9. Етапи розробки

### Етап 1: MVP (4 тижні)
- Базовий збір даних з Yahoo Finance
- Простий LLM аналіз
- OpenSearch налаштування
- API для поточних рекомендацій

### Етап 2: Автоматизація (3 тижні)
- Celery scheduler для щоденних задач
- Додаткові джерела даних
- Покращений AI аналіз
- Щоденні звіти

### Етап 3: Розширення (3 тижні)
- Summary звіти
- Історичні дані та аналітика
- API для всіх функцій
- Моніторинг та логування

### Етап 4: Оптимізація (2 тижні)
- Performance туннінг
- Error handling
- Documentation
- Production deployment

## 10. Критерії приймання

### 10.1 Функціональні критерії
- ✅ Щоденний збір даних відбувається автоматично
- ✅ AI генерує рекомендації для обох категорій
- ✅ API повертає валідні дані
- ✅ Звіти зберігаються та доступні

### 10.2 Технічні критерії
- ✅ Система витримує навантаження 35+ акцій
- ✅ Час обробки <20 хвилин
- ✅ API response time <2 секунди
- ✅ Uptime >95% у перший місяць

### 10.3 Якісні критерії
- ✅ Рекомендації мають логічне обґрунтування
- ✅ Звіти читабельні та інформативні
- ✅ Система надійно працює без втручання
- ✅ Документація повна та актуальна

Даний проект створить надійну основу для автоматизованого інвестиційного аналізу з можливістю подальшого розширення та вдосконалення.
