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

### Процесс сбора (v4.0)
1. **Data Loader Service** запрашивает листинги через `searchPropertyByPlaceId`
2. **Detail Fetcher** обогащает данные через `getPropertyDetails` API
3. **Image Downloader** скачивает до 20+ изображений на каждый листинг (из detailed API)
4. **CLIP Processor** извлекает 512-мерные визуальные эмбеддинги для каждого изображения
5. **Mean+Max+Std Aggregation** комбинирует эмбеддинги в 1536-мерный вектор (Mean 512 + Max 512 + Std 512)
6. **PCA Reduction** сжимает эмбеддинги до 100 компонент (81% variance)
7. **PostgreSQL + pgvector** сохраняет данные для обучения и поиска

### Покрытие регионов
- **New York Area**: Manhattan, Brooklyn, Queens, Bronx
- **Los Angeles Area**: West Hollywood, Beverly Hills, Santa Monica, Downtown LA, Marina del Rey

### Покрытие города
- **99.9%** листингов имеют указанный город (из detailed API)
- Основные города: Brooklyn (188), New York (109), West Hollywood (73), Santa Monica (67)

---

## Структура датасета (v4.0)

Датасет сохранен в формате Parquet: `data/training_dataset_v4.parquet`

### Статистика
- **Всего записей:** 711
- **Всего признаков:** 166 (excluding 'id'), из них используется 40 (feature selection)
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

#### 4. PCA-сжатые CLIP Embeddings (100 признаков, используется 27)

- `pca_0` ... `pca_99` (float) - 100-мерный вектор (PCA от 1536-мерных Mean+Max+Std embeddings)
- **Explained variance:** 81.01%
- **Aggregation method:** Mean (512d) + Max (512d) + Std (512d) = 1536d → PCA to 100d

---

## Статистика модели v4.0

### Feature Selection
- **Total features available:** 164
- **Selected features:** 40 (top features by importance)
- **Importance captured:** 79.2%

### Важность признаков (Top 10)
1. `lat` - 25.6%
2. `is_private_room` - 10.9%
3. `pca_1` - 5.0%
4. `distance_to_center_nyc` - 4.5%
5. `distance_to_center_la` - 3.4%
6. `lng` - 2.2%
7. `person_capacity` - 1.7%
8. `beds` - 1.5%
9. `pca_44` - 1.4%
10. `pca_27` - 1.4%

### Метрики качества (Cross-Validation)
- **RMSE:** $194 ± $14
- **MAE:** $114 ± $8
- **MAPE:** 60.1% ± 4.1%

### Hyperparameters (Optuna-tuned)
- **Iterations:** 1386
- **Learning rate:** 0.0225
- **Depth:** 6
- **L2 regularization:** 19.17
- **Min data in leaf:** 26

---

## Организация данных

```
data/
├── raw/
│   ├── search/          # JSON от searchPropertyByPlaceId
│   └── details/         # JSON от getPropertyDetails (721 файлов)
├── images/              # Изображения (~20 на листинг)
├── training_dataset_v4.parquet
├── train.parquet
└── test.parquet
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
python3 scripts/prepare_training_dataset.py --output data/training_dataset_v4.parquet

# 5. Split and train
python3 -c "from sklearn.model_selection import train_test_split; ..."
cd services/ml_inference && python3 train.py ...
```

---

## Планы развития

### Краткосрочные (v4.1)
- [ ] Расширение географии: London, Paris, Miami
- [ ] Feature engineering: price/bedroom ratios, neighborhood stats
- [ ] Увеличение датасета до 2,000+ листингов

### Среднесрочные (v5.0)
- [ ] Airflow DAG для автоматического обновления
- [ ] Model Registry (MLflow) для версионирования
- [ ] Drift detection и автоматический retrain
- [ ] Увеличение датасета до 5,000+ листингов

### Метрики успеха
| Метрика | v4.0 | Цель |
|---------|------|------|
| MAPE | 60.1% | < 25% |
| Metadata importance | 79.2% | > 80% |
| City coverage | 99.9% | 100% |
| Listings | 711 | 5,000+ |
| Features (selected) | 40 | 50+ |
