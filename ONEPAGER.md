# Multimodal Real Estate Price Prediction System
## One-Pager: Описание проекта

---

## Бизнес-задача

**Проблема:** Владельцы недвижимости на рынке краткосрочной аренды (Airbnb) сталкиваются с трудностями определения оптимальной цены. Субъективная оценка приводит к потере прибыли или длительному простою объектов.

**Решение:** Мультимодальная ML-система, которая автоматически предсказывает справедливую рыночную цену на основе визуальных характеристик (фотографий) и метаданных (местоположение, площадь, рейтинг и т.д.).

**Ценность:**
- Мгновенная объективная оценка (вместо дней анализа)
- Оптимизация прибыли (баланс между ценой и заполняемостью)
- Data-driven решения на основе тысяч объектов

---

## Данные

**Источник:** Airbnb API (RapidAPI)

**Объем:**
- ~1,000+ листингов (NYC, Manhattan, Brooklyn, Queens)
- До 20 изображений на листинг
- Метаданные: цена, местоположение, рейтинг, тип недвижимости

**Обработка:**
- CLIP embeddings (512-мерные векторы) из изображений
- Mean+Max+Std aggregation для множественных изображений (1536-мерный вектор)
- PCA reduction: 1536 → 100 компонент (81% variance)
- PostgreSQL + pgvector для хранения и векторного поиска

---

## 🛠 Технологический стек

### Backend
- **Python 3.12** - основной язык разработки
- **PostgreSQL 16** + **pgvector** - база данных с векторным поиском
- **Kafka** (Confluent) - брокер сообщений для асинхронной обработки
- **FastAPI** - ML inference service
- **Docker & Docker Compose** - контейнеризация

### ML/AI
- **OpenAI CLIP** (ViT-B/32) - извлечение визуальных признаков
- **PyTorch** - фреймворк для ML
- **CatBoost** - модель предсказания цен
- **MPS** (Apple Silicon) - GPU acceleration для обработки изображений

### Frontend & Monitoring
- **Streamlit** - веб-интерфейс для взаимодействия с моделью
- **Grafana** - мониторинг метрик и дашборды
- **Plotly** - интерактивные визуализации

### DevOps
- **Docker Compose** - оркестрация сервисов
- **Healthchecks** - мониторинг состояния сервисов
- **Structured logging** - централизованное логирование

---

## Метрики и производительность

### Текущие метрики системы
- **Обработка изображений:** ~0.5-1 сек на листинг (MPS acceleration)
- **Сбор данных:** ~0.3 листинга/сек
- **Хранение:** 1,000+ листингов с embeddings
- **Векторный поиск:** < 100ms для топ-10 похожих объектов

### Метрики ML-модели (v4.0)
- **Model:** CatBoost Regressor (Optuna-tuned)
- **Features:** 40 selected features (PCA embeddings + metadata)
- **Embeddings:** Mean+Max+Std (1536d) → PCA (100d, 81% variance)
- **Performance:** Cross-validation MAPE 60.1% ± 4.1%
- **Время инференса:** < 100ms на запрос
- **Throughput:** 100+ запросов/минуту

---

## Архитектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  Airbnb API │────▶│ Data Loader  │────▶│ PostgreSQL  │────▶│ Kafka Topic │
│ (Search +   │     │ (CLIP +      │     │ (pgvector,  │     │             │
│  Details)   │     │  Mean+Max+   │     │  vector(1536))│   │             │
│             │     │  Std, PCA)   │     │             │     │             │
└─────────────┘     └──────────────┘     └──────┬──────┘     └──────┬──────┘
                                                  │                   │
                                                  ▼                   ▼
                                         ┌──────────────┐     ┌──────────────┐
                                         │ ML Inference │◀────│  Streamlit   │
                                         │ (CatBoost    │     │      UI      │
                                         │  v4.0, 40    │     │              │
                                         │  features)   │     │              │
                                         └──────┬───────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │   Grafana    │
                                         │  Monitoring  │
                                         └──────────────┘
```

---

## Статус реализации

### Все компоненты реализованы
- Data ingestion pipeline (Airbnb Search + Details API, CLIP, Mean+Max+Std, PCA)
- PostgreSQL + pgvector (vector(1536)) для векторного поиска
- Kafka для асинхронной обработки
- ML inference service (CatBoost v4.0 с feature selection + FastAPI)
- Streamlit UI (инференс, аналитика, история)
- Grafana мониторинг (дашборды)

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd project

# 2. (Опционально) Создать .env для сбора новых данных
# cp .env.example .env
# Для запуска с существующими данными .env не нужен

# 3. Запустить все сервисы
docker-compose up -d

# 4. Открыть интерфейсы
# UI: http://localhost:8501
# API: http://localhost:8000/docs
# Grafana: http://localhost:3000 (admin/admin)
```

---

## Веб-интерфейсы

| Сервис | URL | Описание |
|--------|-----|----------|
| Streamlit UI | localhost:8501 | Инференс и аналитика |
| ML API | localhost:8000 | FastAPI + Swagger |
| Grafana | localhost:3000 | Мониторинг метрик |

---

**Проект для курса MLOps HSE 2025**

