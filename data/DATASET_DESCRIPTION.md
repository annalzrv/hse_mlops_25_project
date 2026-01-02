# Training Dataset Description

## Методология сбора данных

### Источник данных
Данные собраны из **Airbnb API** через сервис RapidAPI (airbnb19.p.rapidapi.com). Используются два эндпоинта:
1. **searchPropertyByPlaceId** - поиск листингов по локации
2. **getPropertyDetails** - детальная информация о каждом листинге

### Почему Airbnb?
1. **Реальные рыночные данные** - актуальные цены от реальных хозяев
2. **Мультимодальность** - комбинация визуальных и структурированных данных
3. **Масштаб** - тысячи объектов в популярных локациях
4. **Бизнес-релевантность** - динамическое ценообразование на рынке краткосрочной аренды

### Процесс сбора (v3.0)
1. **Data Loader Service** запрашивает листинги через `searchPropertyByPlaceId`
2. **Detail Fetcher** обогащает данные через `getPropertyDetails` API
3. **Image Downloader** скачивает до 20+ изображений на каждый листинг (из detailed API)
4. **CLIP Processor** извлекает 512-мерные визуальные эмбеддинги
5. **PCA Reduction** сжимает эмбеддинги до 50 компонент (97% variance)
6. **Mean Pooling** агрегирует эмбеддинги нескольких изображений
7. **PostgreSQL + pgvector** сохраняет данные для обучения и поиска

### Покрытие регионов
- **New York Area**: Manhattan, Brooklyn, Queens, Bronx
- **Los Angeles Area**: West Hollywood, Beverly Hills, Santa Monica, Downtown LA, Marina del Rey

### Покрытие города
- **~99%** листингов имеют указанный город (из detailed API)
- Основные города: Brooklyn (189), New York (109), West Hollywood (73), Santa Monica (70)

---

## Структура датасета (v3.0)

Датасет сохранен в формате Parquet: `data/training_dataset_v3.parquet`

### Статистика
- **Всего записей:** 713
- **Всего признаков:** 115 (excluding 'id')
- **Целевая переменная:** `price` (цена за ночь в USD)

### Столбцы датасета

#### 1. Идентификатор
- `id` (string) - уникальный идентификатор листинга

#### 2. Целевая переменная
- `price` (float) - цена за ночь в USD (целевая переменная для обучения модели)

#### 3. Метаданные (65 признаков)

**Рейтинг и отзывы:**
- `rating` (float) - агрегированный рейтинг (среднее от detailed ratings)
- `has_rating` (float) - флаг наличия рейтинга (1.0 если есть)
- `num_reviews` (float) - количество отзывов
- `has_reviews` (float) - флаг наличия отзывов

**Детальные рейтинги (из getPropertyDetails):**
- `cleanliness_rating` (float) - рейтинг чистоты
- `location_rating` (float) - рейтинг локации
- `value_rating` (float) - рейтинг соотношения цена/качество
- `communication_rating` (float) - рейтинг коммуникации с хостом
- `checkin_rating` (float) - рейтинг заселения
- `accuracy_rating` (float) - рейтинг точности описания

**Характеристики недвижимости:**
- `person_capacity` (float) - вместимость (количество гостей)
- `bedrooms` (float) - количество спален
- `beds` (float) - количество кроватей
- `bathrooms` (float) - количество ванных комнат

**Тип недвижимости:**
- `is_entire_place` (float) - целая квартира/дом
- `is_private_room` (float) - отдельная комната
- `is_shared_room` (float) - общая комната
- `is_hotel` (float) - номер в отеле
- `room_type_entire` / `room_type_private` / `room_type_shared` (float)

**Удобства (amenities):**
- `has_wifi`, `has_kitchen`, `has_washer`, `has_dryer`, `has_air_conditioning`
- `has_heating`, `has_tv`, `has_pool`, `has_hot_tub`, `has_gym`, `has_elevator`
- `has_parking`, `has_smoke_alarm`, `has_carbon_monoxide_alarm`, `has_fire_extinguisher`
- `has_dishwasher`, `has_refrigerator`, `has_microwave`, `has_oven`, `has_coffee_maker`
- `has_self_check_in`, `has_lockbox`, `has_keypad`, `has_smart_lock`
- `has_beach_access`, `has_waterfront`, `has_lake_access`
- `has_patio_or_balcony`, `has_backyard`, `has_garden`
- `has_crib`, `has_high_chair`, `has_pets_allowed`

**Локация:**
- `city` (string) - город/район (Brooklyn, New York, Santa Monica, etc.)
- `lat` (float) - широта
- `lng` (float) - долгота
- `distance_to_center_la` (float) - расстояние до центра LA в км
- `distance_to_center_nyc` (float) - расстояние до центра NYC в км

**Текстовые признаки из name:**
- `name_length` (float) - длина названия в символах
- `name_word_count` (float) - количество слов в названии
- `has_mention_of_luxury` / `has_mention_of_beach` / `has_mention_of_pool` / `has_mention_of_parking` (float)

#### 4. PCA-сжатые CLIP Embeddings (50 признаков)

- `pca_0` ... `pca_49` (float) - 50-мерный вектор (PCA от 512-мерных CLIP embeddings)
- **Explained variance:** 97.24%

---

## Статистика модели v3.0

### Важность признаков
| Группа | Доля важности |
|--------|---------------|
| Metadata features | 45.2% |
| PCA embeddings | 54.8% |

### Топ-10 признаков по важности
1. `lat` - 18.9%
2. `pca_1` - 17.1%
3. `is_private_room` - 6.7%
4. `pca_11` - 5.0%
5. `location_rating` - 4.0%
6. `pca_0` - 3.6%
7. `distance_to_center_nyc` - 3.4%
8. `distance_to_center_la` - 3.3%
9. `person_capacity` - 2.5%
10. `lng` - 1.9%

### Метрики качества (Test set)
- **RMSE:** $115.01
- **MAE:** $76.02
- **MAPE:** 52.05%

---

## Организация данных

```
data/
├── raw/
│   ├── search/          # JSON от searchPropertyByPlaceId
│   └── details/         # JSON от getPropertyDetails (721 файлов)
├── images/              # Изображения (~20 на листинг)
├── training_dataset_v3.parquet
├── train_v3.parquet
└── test_v3.parquet
```

---

## Обновление датасета

```bash
# 1. Fetch new listing details
python3 services/data_loader/detail_fetcher.py --data-dir ./data

# 2. Parse details and update DB
python3 services/data_loader/detail_parser.py --data-dir ./data

# 3. Download images from detailed data
python3 services/data_loader/detail_image_downloader.py --data-dir ./data

# 4. Generate training dataset with PCA
python3 scripts/prepare_training_dataset.py --output data/training_dataset_v3.parquet

# 5. Split and train
python3 -c "from sklearn.model_selection import train_test_split; ..."
cd services/ml_inference && python3 train.py ...
```

---

## Планы развития

### Краткосрочные (v3.1)
- [ ] Расширение географии: London, Paris, Miami
- [ ] Feature engineering: price/bedroom ratios, neighborhood stats

### Среднесрочные (v4.0)
- [ ] Airflow DAG для автоматического обновления
- [ ] Model Registry (MLflow) для версионирования
- [ ] Drift detection и автоматический retrain

### Метрики успеха
| Метрика | v3.0 | Цель |
|---------|------|------|
| MAPE | 52% | < 25% |
| Metadata importance | 45% | > 50% |
| City coverage | 99% | 100% |
| Listings | 713 | 5,000+ |
