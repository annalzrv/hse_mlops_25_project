# Как смотреть логи в реальном времени

## Текущий статус

**В базе данных:** 673 листинга
**В процессе (собрано, но еще не обработано):** 2 листинга
**Изображения:** ~882 MB локально

## Команды для просмотра логов

### 1. Логи в реальном времени (follow mode)

```bash
# Все логи пайплайна в реальном времени
docker-compose logs -f data_loader

# Только важные события (обработка листингов)
docker-compose logs -f data_loader | grep -E "(Processing listing|Successfully processed|Fetched.*new listings)"
```

### 2. Последние N строк

```bash
# Последние 50 строк
docker-compose logs --tail=50 data_loader

# Последние 100 строк с фильтром
docker-compose logs --tail=100 data_loader | grep "Processing listing"
```

### 3. Логи за определенный период

```bash
# Логи с временной меткой
docker-compose logs --since 10m data_loader

# Логи между временем
docker-compose logs --since 2025-12-31T23:00:00 --until 2025-12-31T23:30:00 data_loader
```

### 4. Мониторинг прогресса

```bash
# Использовать скрипт мониторинга
./scripts/check_progress.sh

# Или вручную проверить БД
docker-compose exec -T postgres psql -U mlops -d real_estate -c "SELECT COUNT(*) FROM listings;"
```

## Понимание логов

**Этапы обработки:**

1. **API Fetching** (сбор из API):
   ```
   Fetched X new listings from place_id '...' page Y
   ```
   - Это означает, что листинги собраны в память
   - Еще НЕ сохранены в БД

2. **Processing** (обработка):
   ```
   Processing listing 12345678 (N)
   ```
   - Началась обработка листинга
   - Скачиваются изображения
   - Генерируются embeddings

3. **Saving** (сохранение):
   ```
   Successfully processed listing 12345678
   ```
   - Листинг сохранен в БД
   - Теперь он в базе данных

## Разница между "в процессе" и "в БД"

**"В процессе" (Total: X/4120):**
- Листинги собраны из API
- Находятся в памяти Python процесса
- Еще не обработаны (нет изображений, embeddings)
- Еще не сохранены в PostgreSQL

**"В БД":**
- Листинги полностью обработаны
- Изображения скачаны
- Embeddings сгенерированы
- Сохранены в PostgreSQL

**Пример:**
- Лог: "Total: 2/4120" → 2 листинга в памяти, еще не в БД
- БД: 673 листинга → это уже обработанные и сохраненные

## Рекомендации

**Для постоянного мониторинга:**
```bash
# Открыть отдельный терминал и запустить:
watch -n 5 './scripts/check_progress.sh'
```

**Для детального просмотра:**
```bash
# В реальном времени с фильтрацией
docker-compose logs -f data_loader | grep -E "(Processing|Successfully|Failed|Error)"
```

