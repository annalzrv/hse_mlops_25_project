#!/bin/bash
# Script to load seed data into PostgreSQL
# Run this after docker-compose up and database initialization

set -e

echo "Loading seed data into PostgreSQL..."

# Check if PostgreSQL is ready
until docker-compose exec -T postgres pg_isready -U mlops > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Load data using psql
docker-compose exec -T postgres psql -U mlops -d real_estate < scripts/load_seed_data.sql

echo "Seed data loaded successfully!"
echo "Listings: $(docker-compose exec -T postgres psql -U mlops -d real_estate -t -c 'SELECT COUNT(*) FROM listings;')"
echo "Predictions: $(docker-compose exec -T postgres psql -U mlops -d real_estate -t -c 'SELECT COUNT(*) FROM predictions;')"
echo "Amenities: $(docker-compose exec -T postgres psql -U mlops -d real_estate -t -c 'SELECT COUNT(*) FROM listing_amenities;')"

