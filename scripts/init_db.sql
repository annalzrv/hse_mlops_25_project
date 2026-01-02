CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS listings (
    id VARCHAR(255) PRIMARY KEY,
    price FLOAT,
    lat FLOAT,
    lng FLOAT,
    name TEXT,
    rating FLOAT,
    embedding vector(512),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS listings_embedding_idx ON listings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS listings_price_idx ON listings(price);
CREATE INDEX IF NOT EXISTS listings_location_idx ON listings(lat, lng);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(255),
    predicted_price FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50) DEFAULT 'v1.0'
);

CREATE INDEX IF NOT EXISTS predictions_listing_id_idx ON predictions(listing_id);
CREATE INDEX IF NOT EXISTS predictions_created_at_idx ON predictions(created_at);

