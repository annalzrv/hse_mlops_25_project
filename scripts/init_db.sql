CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS listings (
    id VARCHAR(255) PRIMARY KEY,
    price FLOAT,
    lat FLOAT,
    lng FLOAT,
    name TEXT,
    rating FLOAT,
    embedding vector(512),
    created_at TIMESTAMP DEFAULT NOW(),
    -- New detailed fields (Phase 2)
    property_type VARCHAR(100),
    room_type VARCHAR(100),
    person_capacity INT,
    bedrooms INT,
    beds INT,
    bathrooms FLOAT,
    cleanliness_rating FLOAT,
    location_rating FLOAT,
    value_rating FLOAT,
    communication_rating FLOAT,
    checkin_rating FLOAT,
    accuracy_rating FLOAT,
    review_count INT,
    description TEXT,
    details_fetched_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS listings_embedding_idx ON listings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS listings_price_idx ON listings(price);
CREATE INDEX IF NOT EXISTS listings_location_idx ON listings(lat, lng);
CREATE INDEX IF NOT EXISTS listings_property_type_idx ON listings(property_type);
CREATE INDEX IF NOT EXISTS listings_room_type_idx ON listings(room_type);

-- Amenities table for normalized amenity storage
CREATE TABLE IF NOT EXISTS listing_amenities (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(255) REFERENCES listings(id) ON DELETE CASCADE,
    amenity_name VARCHAR(200) NOT NULL,
    amenity_category VARCHAR(100),
    UNIQUE(listing_id, amenity_name)
);

CREATE INDEX IF NOT EXISTS listing_amenities_listing_id_idx ON listing_amenities(listing_id);
CREATE INDEX IF NOT EXISTS listing_amenities_name_idx ON listing_amenities(amenity_name);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(255),
    predicted_price FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50) DEFAULT 'v1.0'
);

CREATE INDEX IF NOT EXISTS predictions_listing_id_idx ON predictions(listing_id);
CREATE INDEX IF NOT EXISTS predictions_created_at_idx ON predictions(created_at);

