#!/usr/bin/env python3
"""
Script to update prices in database to price per night.
To be run inside data_loader container.
"""

import os
import json
import psycopg2
from pathlib import Path
from typing import Dict, Optional
import re

def extract_price_per_night_from_json(listing: dict) -> Optional[float]:
    """Extract price per night from listing dict"""
    price = None
    nights = None

    if "structuredDisplayPrice" in listing:
        primary_line = listing.get("structuredDisplayPrice", {}).get("primaryLine", {})
        price_str = primary_line.get("price") or primary_line.get("discountedPrice") or primary_line.get("originalPrice")
        qualifier = primary_line.get("qualifier", "")

        if price_str:
            try:
                price = float(price_str.replace("$", "").replace(",", "").strip())

                if qualifier:
                    nights_match = re.search(r'(\d+)\s*(?:night|nights)', qualifier, re.IGNORECASE)
                    if nights_match:
                        nights = int(nights_match.group(1))
                    elif re.search(r'per\s+night', qualifier, re.IGNORECASE):
                        nights = 1
            except (ValueError, AttributeError):
                pass

    if price is None and "pricingQuote" in listing:
        primary_line = listing.get("pricingQuote", {}).get("structuredStayDisplayPrice", {}).get("primaryLine", {})
        price_str = primary_line.get("price")
        qualifier = primary_line.get("qualifier", "")

        if price_str:
            try:
                price = float(price_str.replace("$", "").replace(",", "").strip())

                if qualifier:
                    nights_match = re.search(r'(\d+)\s*(?:night|nights)', qualifier, re.IGNORECASE)
                    if nights_match:
                        nights = int(nights_match.group(1))
                    elif re.search(r'per\s+night', qualifier, re.IGNORECASE):
                        nights = 1
            except (ValueError, AttributeError):
                pass

    if price is not None:
        if nights and nights > 0:
            return price / nights
        else:
            return price

    return None

def load_listings_from_raw_files(raw_dir: Path) -> Dict[str, dict]:
    """Load all listings from raw JSON files"""
    listings_map = {}

    for json_file in raw_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            listings = []
            if "data" in data and "list" in data["data"]:
                listings = data["data"]["list"]
            elif "list" in data:
                listings = data["list"]

            for listing in listings:
                listing_data = listing.get("listing", listing)
                listing_id = str(listing_data.get("id", ""))
                if listing_id and listing_id != "unknown":
                    listings_map[listing_id] = listing
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

    return listings_map

def update_database_prices(conn_params: dict, listings_map: Dict[str, dict]):
    """Update prices in database"""
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM listings")
    db_ids = {row[0] for row in cursor.fetchall()}

    print(f"Found {len(db_ids)} listings in database")
    print(f"Found {len(listings_map)} listings in raw JSON files")

    updated_count = 0
    not_found_count = 0

    for listing_id in db_ids:
        if listing_id in listings_map:
            listing = listings_map[listing_id]
            price_per_night = extract_price_per_night_from_json(listing)

            if price_per_night is not None:
                cursor.execute(
                    "UPDATE listings SET price = %s WHERE id = %s",
                    (price_per_night, listing_id)
                )
                updated_count += 1
                if updated_count % 100 == 0:
                    print(f"Updated {updated_count} listings...")
                    conn.commit()
        else:
            not_found_count += 1

    conn.commit()
    cursor.close()
    conn.close()

    print("\nUpdate complete:")
    print(f"  Updated: {updated_count}")
    print(f"  Not found in raw files: {not_found_count}")

if __name__ == "__main__":
    raw_dir = Path("/app/data/raw")

    conn_params = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "real_estate"),
        "user": os.getenv("POSTGRES_USER", "mlops"),
        "password": os.getenv("POSTGRES_PASSWORD", "mlops123")
    }

    print("Loading listings from raw JSON files...")
    listings_map = load_listings_from_raw_files(raw_dir)

    print("\nUpdating database prices...")
    update_database_prices(conn_params, listings_map)

