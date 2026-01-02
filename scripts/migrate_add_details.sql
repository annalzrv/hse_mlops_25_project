-- Migration: Add detailed listing columns and amenities table
-- Run this on an existing database to add new fields for enriched data

-- Add new columns to listings table (using IF NOT EXISTS pattern with DO blocks)
DO $$ 
BEGIN
    -- City from detailed data
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'city') THEN
        ALTER TABLE listings ADD COLUMN city VARCHAR(100);
    END IF;

    -- Property details
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'property_type') THEN
        ALTER TABLE listings ADD COLUMN property_type VARCHAR(100);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'room_type') THEN
        ALTER TABLE listings ADD COLUMN room_type VARCHAR(100);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'person_capacity') THEN
        ALTER TABLE listings ADD COLUMN person_capacity INT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'bedrooms') THEN
        ALTER TABLE listings ADD COLUMN bedrooms INT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'beds') THEN
        ALTER TABLE listings ADD COLUMN beds INT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'bathrooms') THEN
        ALTER TABLE listings ADD COLUMN bathrooms FLOAT;
    END IF;
    
    -- Ratings
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'cleanliness_rating') THEN
        ALTER TABLE listings ADD COLUMN cleanliness_rating FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'location_rating') THEN
        ALTER TABLE listings ADD COLUMN location_rating FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'value_rating') THEN
        ALTER TABLE listings ADD COLUMN value_rating FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'communication_rating') THEN
        ALTER TABLE listings ADD COLUMN communication_rating FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'checkin_rating') THEN
        ALTER TABLE listings ADD COLUMN checkin_rating FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'accuracy_rating') THEN
        ALTER TABLE listings ADD COLUMN accuracy_rating FLOAT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'review_count') THEN
        ALTER TABLE listings ADD COLUMN review_count INT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'description') THEN
        ALTER TABLE listings ADD COLUMN description TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'listings' AND column_name = 'details_fetched_at') THEN
        ALTER TABLE listings ADD COLUMN details_fetched_at TIMESTAMP;
    END IF;
END $$;

-- Create amenities table
CREATE TABLE IF NOT EXISTS listing_amenities (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(255) REFERENCES listings(id) ON DELETE CASCADE,
    amenity_name VARCHAR(200) NOT NULL,
    amenity_category VARCHAR(100),
    UNIQUE(listing_id, amenity_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS listings_property_type_idx ON listings(property_type);
CREATE INDEX IF NOT EXISTS listings_room_type_idx ON listings(room_type);
CREATE INDEX IF NOT EXISTS listing_amenities_listing_id_idx ON listing_amenities(listing_id);
CREATE INDEX IF NOT EXISTS listing_amenities_name_idx ON listing_amenities(amenity_name);

-- Verify migration
SELECT 
    'Migration complete!' AS status,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'listings') AS total_listing_columns,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'listing_amenities') AS amenities_table_exists;

