-- Load seed data for reviewers
-- This script loads sample data without embeddings (embeddings are too large for git)
-- Embeddings are optional - the service works with metadata features only
-- Using \copy (client-side) - files are accessible from seed-data-loader container

-- Create temporary tables for loading
CREATE TEMP TABLE temp_listings (LIKE listings INCLUDING ALL);
CREATE TEMP TABLE temp_predictions (LIKE predictions INCLUDING ALL);
CREATE TEMP TABLE temp_amenities (LIKE listing_amenities INCLUDING ALL);

-- Load into temporary tables
\copy temp_listings(id, price, lat, lng, name, rating, property_type, room_type, person_capacity, bedrooms, beds, bathrooms, cleanliness_rating, location_rating, value_rating, communication_rating, checkin_rating, accuracy_rating, review_count, description, city, created_at) FROM '/scripts/listings_data.csv' WITH (FORMAT csv, HEADER true, NULL '');

\copy temp_predictions(listing_id, predicted_price, created_at, model_version) FROM '/scripts/predictions_data.csv' WITH (FORMAT csv, HEADER true, NULL '');

\copy temp_amenities(listing_id, amenity_name, amenity_category) FROM '/scripts/amenities_data.csv' WITH (FORMAT csv, HEADER true, NULL '');

-- Insert into actual tables, ignoring duplicates
INSERT INTO listings SELECT * FROM temp_listings ON CONFLICT (id) DO NOTHING;
INSERT INTO predictions SELECT * FROM temp_predictions ON CONFLICT (id) DO NOTHING;
INSERT INTO listing_amenities SELECT * FROM temp_amenities ON CONFLICT (listing_id, amenity_name) DO NOTHING;

-- Update sequences
SELECT setval('predictions_id_seq', COALESCE((SELECT MAX(id) FROM predictions), 1), true);
SELECT setval('listing_amenities_id_seq', COALESCE((SELECT MAX(id) FROM listing_amenities), 1), true);

