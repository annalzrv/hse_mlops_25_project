#!/bin/bash
# Auto-load seed data script
# This script checks if data exists and loads it if needed
# Used by docker-compose seed_data_loader service

set -e

echo "=== Seed Data Loader ==="
echo "Checking if seed data needs to be loaded..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -U mlops -h postgres > /dev/null 2>&1; do
  echo "  PostgreSQL not ready yet, waiting..."
  sleep 2
done
echo "PostgreSQL is ready!"

# Wait for tables to be created (init_db.sql runs on first start)
echo "Waiting for database tables to be created..."
sleep 5

# Check if CSV files exist
if [ ! -f "/scripts/listings_data.csv" ]; then
  echo "ERROR: /scripts/listings_data.csv not found!"
  exit 1
fi
echo "CSV files found ✓"

# Check if listings table exists
TABLE_EXISTS=$(psql -U mlops -h postgres -d real_estate -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'listings');" 2>/dev/null | xargs || echo "false")

if [ "$TABLE_EXISTS" != "t" ]; then
  echo "ERROR: listings table does not exist!"
  exit 1
fi
echo "Database tables exist ✓"

# Check if listings table has data (with retry and proper integer conversion)
LISTINGS_COUNT=0
for i in {1..5}; do
  COUNT_STR=$(psql -U mlops -h postgres -d real_estate -t -c "SELECT COUNT(*) FROM listings WHERE price IS NOT NULL;" 2>/dev/null | xargs || echo "0")
  # Remove any whitespace and convert to integer
  LISTINGS_COUNT=$((COUNT_STR + 0))
  if [ "$LISTINGS_COUNT" -ge 0 ] 2>/dev/null; then
    break
  fi
  echo "  Waiting for database query to work... (attempt $i/5)"
  sleep 2
done

echo "Current listings count: $LISTINGS_COUNT"

if [ "$LISTINGS_COUNT" -eq 0 ]; then
  echo ""
  echo "No data found. Loading seed data..."
  
  # Load data
  echo "Loading listings..."
  if psql -U mlops -h postgres -d real_estate -f /scripts/load_seed_data.sql > /tmp/load_output.log 2>&1; then
    LOAD_SUCCESS=true
  else
    # Check if errors are just duplicates (data already partially loaded)
    if grep -q "duplicate key" /tmp/load_output.log; then
      echo "  Warning: Some duplicate keys (data may already be partially loaded)"
      LOAD_SUCCESS=true
    else
      echo "  ERROR: Failed to load seed data!"
      cat /tmp/load_output.log
      LOAD_SUCCESS=false
    fi
  fi
  
  # Verify data was loaded
  FINAL_COUNT_STR=$(psql -U mlops -h postgres -d real_estate -t -c "SELECT COUNT(*) FROM listings WHERE price IS NOT NULL;" 2>/dev/null | xargs || echo "0")
  FINAL_COUNT=$((FINAL_COUNT_STR + 0))
  
  if [ "$FINAL_COUNT" -gt 0 ]; then
    echo ""
    echo "✓ Seed data loaded successfully!"
    echo "  Listings: $FINAL_COUNT"
    PRED_COUNT=$(psql -U mlops -h postgres -d real_estate -t -c "SELECT COUNT(*) FROM predictions;" 2>/dev/null | xargs || echo "0")
    AMEN_COUNT=$(psql -U mlops -h postgres -d real_estate -t -c "SELECT COUNT(*) FROM listing_amenities;" 2>/dev/null | xargs || echo "0")
    echo "  Predictions: $PRED_COUNT"
    echo "  Amenities: $AMEN_COUNT"
  else
    echo ""
    echo "✗ ERROR: Data loading failed! Final count is 0."
    if [ -f /tmp/load_output.log ]; then
      echo "Error output:"
      cat /tmp/load_output.log
    fi
    exit 1
  fi
else
  echo "Data already exists ($LISTINGS_COUNT listings). Skipping seed data load."
fi

echo ""
echo "=== Seed Data Loader Complete ==="
