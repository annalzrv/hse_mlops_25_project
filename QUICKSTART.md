# Quick Start Guide

## Быстрый запуск

### 1. Подготовка

Убедитесь, что файл `.env` создан и содержит ваш RapidAPI ключ:
```bash
cat .env | grep RAPIDAPI_KEY
```

### 2. Запуск инфраструктуры

```bash
# Запустить PostgreSQL, Kafka, Zookeeper
docker-compose up -d postgres zookeeper kafka

# Подождать пока сервисы запустятся (30-60 секунд)
docker-compose ps

# Проверить что PostgreSQL готов
docker-compose exec postgres pg_isready -U mlops

# Проверить что Kafka готов
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### 3. Запуск data loader

```bash
# Запустить data loader
docker-compose up data_loader

# Или в фоне
docker-compose up -d data_loader

# Смотреть логи
docker-compose logs -f data_loader
```

### 4. Проверка результатов

```bash
# Проверить количество записей в БД
docker-compose exec postgres psql -U mlops -d real_estate -c "SELECT COUNT(*) FROM listings;"

# Проверить Kafka сообщения
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic new_listings \
  --from-beginning \
  --max-messages 5

# Проверить изображения
find data/images -name "*.jpg" | wc -l
```

## Локальный запуск (Mac M4)

Если хотите запустить локально для использования MPS:

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить только инфраструктуру
docker-compose up -d postgres zookeeper kafka

# 3. Обновить .env для локального запуска
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5433
# KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# 4. Запустить data loader локально
cd services/data_loader
python main.py
```

## Ожидаемое время выполнения

- 240 объявлений × ~10 изображений = ~2400 изображений
- Время обработки: ~20-30 минут
- Зависит от скорости сети и количества изображений

## Troubleshooting

### Ошибка "Connection refused" к PostgreSQL
```bash
docker-compose restart postgres
docker-compose logs postgres
```

### Ошибка "No module named 'logger'"
Убедитесь что вы запускаете из директории `services/data_loader`:
```bash
cd services/data_loader
python main.py
```

### MPS не работает
Проверьте доступность MPS:
```python
import torch
print(torch.backends.mps.is_available())  # Должно быть True
```

Если False, код автоматически переключится на CPU.

