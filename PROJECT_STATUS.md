# Project Status: Multimodal Real Estate Price Prediction

## Current Status: Production Ready (v4.0)

The system is fully operational with all core components deployed and tested. Model v4.0 uses Mean+Max+Std image aggregation, Optuna-tuned hyperparameters, and feature selection for improved performance.

---

## System Components

### Data Pipeline

| Component | Status | Description |
|-----------|--------|-------------|
| Airbnb Search API | Operational | Async data collection via `searchPropertyByPlaceId` |
| Detail Fetcher | Operational | Enriches listings via `getPropertyDetails` API |
| Detail Parser | Operational | Extracts city, ratings, amenities from detailed data |
| Image Downloader | Operational | Downloads 20+ images per listing from detailed data |
| CLIP Processor | Operational | Extracts 512-dim visual embeddings per image |
| Mean+Max+Std Aggregation | Operational | Combines multiple images into 1536-dim vector |
| PCA Reducer | Operational | Compresses 1536 dims to 100 (81% variance) |
| Kafka Producer | Operational | Publishes new listings to message queue |

### Storage Layer

| Component | Status | Description |
|-----------|--------|-------------|
| PostgreSQL 16 | Operational | Primary database with pgvector extension |
| Listings Table | Operational | Extended schema with 23 columns |
| Amenities Table | Operational | Normalized amenity storage per listing |
| Predictions Table | Operational | Inference results with timestamps |
| Vector Index | Operational | IVFFlat index for similarity search |

### ML Inference

| Component | Status | Description |
|-----------|--------|-------------|
| FastAPI Service | Operational | REST API for predictions |
| CatBoost Model v4.0 | Operational | 40 selected features (Optuna-tuned) |
| PCA Transform | Operational | Applied during inference |
| Kafka Consumer | Operational | Processes new listings from queue |
| Health Checks | Operational | Automated monitoring |

### User Interface

| Component | Status | Description |
|-----------|--------|-------------|
| Streamlit App | Operational | Multi-page web interface |
| Predict Page | Operational | Real-time inference by ID or custom data |
| History Page | Operational | Filterable predictions table |
| Analytics Page | Operational | Interactive charts and statistics |
| API Docs Page | Operational | Links to Swagger UI |

### Monitoring

| Component | Status | Description |
|-----------|--------|-------------|
| Grafana Dashboard | Operational | Real-time metrics visualization |
| Predictions Metrics | Operational | Count, avg, min, max, std dev |
| Time Series | Operational | Predictions over time |
| Drift Monitoring | Operational | Standard deviation tracking |
| Regional Analytics | Operational | LA vs NYC comparison |

---

## Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| Streamlit UI | http://localhost:8501 | Main user interface |
| ML API | http://localhost:8000 | FastAPI inference service |
| API Documentation | http://localhost:8000/docs | OpenAPI/Swagger |
| Grafana | http://localhost:3000 | Monitoring dashboards |
| PostgreSQL | localhost:5433 | Database (external port) |
| Kafka | localhost:9093 | Message broker (external port) |

---

## Data Statistics

| Metric | Value |
|--------|-------|
| Total Listings | 721 |
| Listings with Detailed Data | 719 (99.7%) |
| Listings with City | 710 (99.9%) |
| Regions Covered | 2 (NYC, LA) |
| Cities Covered | 32 |
| Features per Listing | 40 (selected from 164) |
| Metadata Features | 13 |
| PCA Embedding Features | 27 |
| Price Range | $33 - $1,930 |
| Images per Listing | ~20 |

---

## Model Performance (v4.0)

| Metric | Train | Validation | Cross-Validation |
|--------|-------|------------|------------------|
| RMSE | $54.19 | $172.73 | $194 ± $14 |
| MAE | $27.84 | $27.99 | $114 ± $8 |
| MAPE | 24.0% | 59.2% | 60.1% ± 4.1% |

**Note:** Current MAPE is limited by small dataset size (711 samples). Model shows signs of overfitting (train MAPE 24% vs validation 59%). Expanding dataset to 5,000+ listings is planned to improve performance.

### Model Architecture
- Image Embeddings: Mean+Max+Std aggregation (1536 dims) → PCA to 100 dims
- Feature Selection: Top 40 features selected from 164 total (79.2% importance)
- Hyperparameters: Optuna-tuned (30 trials)

### Feature Importance (Top 10)
1. lat (25.6%)
2. is_private_room (10.9%)
3. pca_1 (5.0%)
4. distance_to_center_nyc (4.5%)
5. distance_to_center_la (3.4%)
6. lng (2.2%)
7. person_capacity (1.7%)
8. beds (1.5%)
9. pca_44 (1.4%)
10. pca_27 (1.4%)

---

## Data Organization

```
data/
├── raw/
│   ├── search/      # searchPropertyByPlaceId responses (47 files)
│   └── details/     # getPropertyDetails responses (721 files)
├── images/          # Listing images (~20 per listing)
├── training_dataset_v4.parquet
├── train.parquet
└── test.parquet
```

---

## Known Limitations

1. **Geographic Coverage**: Currently limited to NYC and LA metro areas
2. **Model Accuracy**: CV MAPE ~60%, limited by small dataset (711 samples)
3. **Real-time Updates**: Data collection is manual, not scheduled
4. **Image Processing**: CLIP model requires significant memory (~2GB)
5. **Overfitting**: Train MAPE (24%) much lower than validation (59%), indicating need for more data

---

## Roadmap

### Phase 1: Stability (Complete)
- [x] Core infrastructure deployed
- [x] ML inference operational (v4.0)
- [x] Detailed data enrichment pipeline
- [x] Mean+Max+Std image aggregation
- [x] PCA embedding reduction (1536→100)
- [x] City coverage 99.9%
- [x] Feature selection (top 40 features)
- [x] Optuna hyperparameter tuning
- [x] Monitoring dashboards configured

### Phase 2: Automation (Next)
- [ ] Airflow DAG for scheduled data collection
- [ ] Automated model retraining pipeline
- [ ] CI/CD for model deployment
- [ ] Alerting for prediction drift

### Phase 3: Scale
- [ ] Expand to 10+ cities (Miami, London, Paris)
- [ ] Increase dataset to 10,000+ listings
- [ ] Optimize inference latency to <50ms
- [ ] Add recommendation system (similar listings)

---

## Quick Start

```bash
# Clone repository
git clone <repository-url>
cd project

# (Optional) Create .env for new data collection
# cp .env.example .env
# For running with existing data, .env is not required

# Start all services
docker-compose up -d

# Verify status
docker-compose ps

# Access interfaces
open http://localhost:8501  # UI
open http://localhost:3000  # Grafana (admin/admin)
```

---

## Contact

For issues or questions, please open a GitHub issue in the repository.
