# Training Dataset Description

## Структура датасета

Датасет сохранен в формате Parquet: `data/training_dataset.parquet`

### Статистика
- **Всего записей:** 713
- **Всего признаков:** 527 (excluding 'id')
- **Целевая переменная:** `price` (цена за ночь в USD)

### Столбцы датасета

#### 1. Идентификатор
- `id` (string) - уникальный идентификатор листинга

#### 2. Целевая переменная
- `price` (float) - цена за ночь в USD (целевая переменная для обучения модели)

#### 3. Метаданные (15 признаков)

**Рейтинг и отзывы:**
- `rating` (float) - рейтинг листинга (0.0 если отсутствует)
- `has_rating` (float) - флаг наличия рейтинга (1.0 если есть, 0.0 если нет)
- `num_reviews` (float) - количество отзывов (0.0 если отсутствует)
- `has_reviews` (float) - флаг наличия отзывов (1.0 если есть, 0.0 если нет)

**Локация:**
- `city` (string) - город/район (West Hollywood, Brooklyn, Santa Monica, Los Angeles, New York, Beverly Hills, etc.)
- `lat` (float) - широта
- `lng` (float) - долгота
- `distance_to_center_la` (float) - расстояние до центра LA в км (Haversine)
- `distance_to_center_nyc` (float) - расстояние до центра NYC в км (Haversine)

**Текстовые признаки из name:**
- `name_length` (float) - длина названия в символах
- `name_word_count` (float) - количество слов в названии
- `has_mention_of_luxury` (float) - упоминание luxury/premium/deluxe/executive (1.0/0.0)
- `has_mention_of_beach` (float) - упоминание beach (1.0/0.0)
- `has_mention_of_pool` (float) - упоминание pool (1.0/0.0)
- `has_mention_of_parking` (float) - упоминание parking (1.0/0.0)

#### 4. CLIP Embeddings (512 признаков)

Векторные представления изображений, извлеченные через CLIP модель:
- `embedding_0` ... `embedding_511` (float) - 512-мерный вектор CLIP embeddings

**Примечание:** Embeddings агрегируются через mean pooling, если у листинга несколько изображений.

### Статистика по признакам

#### Целевая переменная (price)
- Среднее: $260.24
- Медиана: $167.40
- Мин: $33.40
- Макс: $1930.00
- Стандартное отклонение: $257.53

#### Локация
- Охватывает LA и NYC регионы
- Координаты: lat (33.92 - 40.91), lng (-118.50 - -73.75)

#### Рейтинг и отзывы
- Большинство листингов не имеют рейтинга (has_rating = 0.0)
- 245/713 листингов имеют отзывы (has_reviews = 1.0)
- Среднее количество отзывов: 63.8 (для листингов с отзывами)
- Максимальное количество отзывов: 1,295

#### Город/Район
- 266/713 листингов имеют указанный город
- Основные города: Santa Monica (53), New York (47), West Hollywood (45), Brooklyn (42), Los Angeles (40), Beverly Hills (24)
- 447 листингов помечены как "Unknown" (город не найден в raw JSON файлах)

## Использование

Датасет используется для обучения мультимодальной модели предсказания цен на недвижимость.

### Формат хранения
- **Формат:** Parquet (эффективное хранение, быстрая загрузка)
- **Местоположение:** `data/training_dataset.parquet`
- **Версионирование:** Рекомендуется сохранять версии при обновлении данных

### Обновление датасета

Для обновления датасета после сбора новых данных запустите:

```bash
POSTGRES_HOST=localhost POSTGRES_PORT=5433 python3 scripts/prepare_training_dataset.py data/training_dataset.parquet
```

Или в Docker контейнере:

```bash
docker-compose exec data_loader python3 /app/scripts/prepare_training_dataset.py /app/data/training_dataset.parquet
```

## Следующие шаги

1. Разделить на train/val/test (обычно 70/15/15 или 80/10/10)
2. Провести feature engineering (нормализация, масштабирование)
3. Обучить модель (CatBoost/XGBoost/Neural Network)
4. Оценить качество модели (RMSE, MAE, MAPE)

