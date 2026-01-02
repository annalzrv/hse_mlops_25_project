"""
Detail Fetcher - Enriches existing listings with detailed data from Airbnb API

Calls getPropertyDetails API for each listing in the database to get:
- Property type, room type, capacity
- Bedrooms, beds, bathrooms
- All ratings (cleanliness, location, value, etc.)
- Amenities
- Full description
"""

import os
import asyncio
import httpx
import json
import time
from pathlib import Path
from typing import List, Dict, Set, Optional
from dotenv import load_dotenv

# Handle both local and Docker imports
try:
    from logger import setup_logger
except ImportError:
    from services.data_loader.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)


class DetailFetcher:
    def __init__(self, data_dir: str = None):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.api_host = os.getenv("RAPIDAPI_HOST", "airbnb19.p.rapidapi.com")
        self.base_url = f"https://{self.api_host}"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        
        # Setup directories
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
        
        self.details_dir = self.data_dir / "raw" / "details"
        self.details_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting
        self.request_delay = 1.0  # Delay between requests in seconds
        self.semaphore = asyncio.Semaphore(1)  # Only 1 concurrent request
        
    def get_already_fetched_ids(self) -> Set[str]:
        """Get set of listing IDs that have already been fetched"""
        fetched_ids = set()
        for json_file in self.details_dir.glob("*.json"):
            # Extract listing ID from filename (format: {listing_id}.json)
            listing_id = json_file.stem
            fetched_ids.add(listing_id)
        
        logger.info(f"Found {len(fetched_ids)} already fetched detail files")
        return fetched_ids
    
    async def fetch_property_details(
        self,
        client: httpx.AsyncClient,
        listing_id: str,
        retries: int = 3
    ) -> Optional[Dict]:
        """Fetch detailed property data from Airbnb API"""
        url = f"{self.base_url}/api/v1/getPropertyDetails"
        
        params = {
            "propertyId": listing_id,
            "currency": "USD"
        }
        
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    logger.info(f"Fetching details for listing {listing_id} (attempt {attempt + 1}/{retries})")
                    
                    response = await client.get(
                        url,
                        headers=self.headers,
                        params=params,
                        timeout=30.0
                    )
                    
                    if response.status_code == 429:
                        wait_time = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    if response.status_code == 404:
                        logger.warning(f"Listing {listing_id} not found (404)")
                        return None
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # Save raw response
                    output_file = self.details_dir / f"{listing_id}.json"
                    with open(output_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    logger.info(f"Successfully fetched and saved details for listing {listing_id}")
                    
                    # Delay before next request
                    await asyncio.sleep(self.request_delay)
                    
                    return data
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error for listing {listing_id} (attempt {attempt + 1}): {e.response.status_code}")
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return None
                        
                except Exception as e:
                    logger.error(f"Error fetching listing {listing_id} (attempt {attempt + 1}): {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return None
        
        return None
    
    async def fetch_all_details(
        self,
        listing_ids: List[str],
        skip_existing: bool = True
    ) -> Dict[str, int]:
        """
        Fetch details for all listings
        
        Args:
            listing_ids: List of listing IDs to fetch
            skip_existing: If True, skip listings that already have detail files
            
        Returns:
            Dictionary with counts: success, failed, skipped
        """
        stats = {"success": 0, "failed": 0, "skipped": 0}
        
        # Filter out already fetched listings if skip_existing is True
        if skip_existing:
            already_fetched = self.get_already_fetched_ids()
            to_fetch = [lid for lid in listing_ids if lid not in already_fetched]
            stats["skipped"] = len(listing_ids) - len(to_fetch)
            logger.info(f"Skipping {stats['skipped']} already fetched listings")
        else:
            to_fetch = listing_ids
        
        logger.info(f"Fetching details for {len(to_fetch)} listings...")
        
        async with httpx.AsyncClient() as client:
            for i, listing_id in enumerate(to_fetch):
                logger.info(f"Progress: {i + 1}/{len(to_fetch)} ({(i + 1) / len(to_fetch) * 100:.1f}%)")
                
                result = await self.fetch_property_details(client, listing_id)
                
                if result is not None:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                
                # Progress log every 50 listings
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {stats['success']} success, {stats['failed']} failed, {stats['skipped']} skipped")
        
        logger.info(f"Completed fetching details: {stats['success']} success, {stats['failed']} failed, {stats['skipped']} skipped")
        return stats


def get_listing_ids_from_db(host: str = None, port: str = None) -> List[str]:
    """Get all listing IDs from the database"""
    import psycopg2
    
    conn_params = {
        "host": host or os.getenv("POSTGRES_HOST", "localhost"),
        "port": port or os.getenv("POSTGRES_PORT", "5433"),
        "database": os.getenv("POSTGRES_DB", "real_estate"),
        "user": os.getenv("POSTGRES_USER", "mlops"),
        "password": os.getenv("POSTGRES_PASSWORD", "mlops123")
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM listings ORDER BY id")
        listing_ids = [str(row[0]) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        logger.info(f"Loaded {len(listing_ids)} listing IDs from database")
        return listing_ids
    except Exception as e:
        logger.error(f"Error loading listing IDs from database: {e}")
        return []


async def main():
    """Main entry point for detail fetching"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch detailed property data from Airbnb API")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Data directory path (default: uses DATA_DIR env var or /app/data)"
    )
    parser.add_argument(
        "--max-listings",
        type=int,
        default=None,
        help="Maximum number of listings to fetch (default: all)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip listings that already have detail files (default: True)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Refetch all listings even if detail files exist"
    )
    parser.add_argument(
        "--db-host",
        type=str,
        default="localhost",
        help="Database host (default: localhost)"
    )
    parser.add_argument(
        "--db-port",
        type=str,
        default="5433",
        help="Database port (default: 5433 for local, 5432 for Docker)"
    )
    
    args = parser.parse_args()
    
    # Get listing IDs from database
    listing_ids = get_listing_ids_from_db(host=args.db_host, port=args.db_port)
    
    if not listing_ids:
        logger.error("No listing IDs found in database")
        return
    
    # Limit if requested
    if args.max_listings:
        listing_ids = listing_ids[:args.max_listings]
        logger.info(f"Limited to {len(listing_ids)} listings")
    
    # Create fetcher and run
    fetcher = DetailFetcher(data_dir=args.data_dir)
    stats = await fetcher.fetch_all_details(listing_ids, skip_existing=args.skip_existing)
    
    print("\n" + "=" * 50)
    print("DETAIL FETCHING COMPLETE")
    print("=" * 50)
    print(f"Success: {stats['success']}")
    print(f"Failed:  {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

