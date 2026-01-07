#!/bin/bash
# Auto-load seed data script
# This script checks if data exists and loads it if needed
# Used by docker-compose seed_data_loader service

set -e

echo "Checking if seed data needs to be loaded..."

# Wait for PostgreSQL to be ready
until pg_isready -U mlops -h postgres > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Check if listings table has data
LISTINGS_COUNT=$(psql -U mlops -h postgres -d real_estate -t -c "SELECT COUNT(*) FROM listings;" 2>/dev/null | xargs || echo "0")

if [ "$LISTINGS_COUNT" -eq "0" ] || [ -z "$LISTINGS_COUNT" ]; then
  echo "No data found. Loading seed data..."
  
  # Load data
  psql -U mlops -h postgres -d real_estate -f /scripts/load_seed_data.sql
  
  echo "Seed data loaded successfully!"
  echo "Listings: $(psql -U mlops -h postgres -d real_estate -t -c 'SELECT COUNT(*) FROM listings;' | xargs)"
  echo "Predictions: $(psql -U mlops -h postgres -d real_estate -t -c 'SELECT COUNT(*) FROM predictions;' | xargs)"
  echo "Amenities: $(psql -U mlops -h postgres -d real_estate -t -c 'SELECT COUNT(*) FROM listing_amenities;' | xargs)"
else
  echo "Data already exists ($LISTINGS_COUNT listings). Skipping seed data load."
fi

