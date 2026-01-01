#!/usr/bin/env python3
"""
Script to delete listings without prices from database.
To be run inside data_loader container.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def delete_listings_without_price():
    """Delete all listings that don't have a price"""
    conn_params = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "real_estate"),
        "user": os.getenv("POSTGRES_USER", "mlops"),
        "password": os.getenv("POSTGRES_PASSWORD", "mlops123")
    }
    
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    # Count before deletion
    cursor.execute("SELECT COUNT(*) FROM listings WHERE price IS NULL")
    count_before = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings")
    total_before = cursor.fetchone()[0]
    
    print(f"Total listings before: {total_before}")
    print(f"Listings without price: {count_before}")
    print(f"Listings with price: {total_before - count_before}")
    
    # Delete listings without price
    cursor.execute("DELETE FROM listings WHERE price IS NULL")
    deleted_count = cursor.rowcount
    
    conn.commit()
    
    # Count after deletion
    cursor.execute("SELECT COUNT(*) FROM listings")
    total_after = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    print(f"\nDeleted {deleted_count} listings without price")
    print(f"Remaining listings: {total_after}")
    print(f"All remaining listings have prices: {total_after > 0 and deleted_count == count_before}")

if __name__ == "__main__":
    delete_listings_without_price()

