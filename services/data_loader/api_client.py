import os
import asyncio
import httpx
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)

class AirbnbAPIClient:
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.api_host = os.getenv("RAPIDAPI_HOST", "airbnb19.p.rapidapi.com")
        
        queries_str = os.getenv("QUERY", "new york")
        self.queries = [q.strip() for q in queries_str.split(",") if q.strip()]
        self.query_index = 0
        
        self.base_url = f"https://{self.api_host}"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        self.raw_data_dir = Path(os.getenv("DATA_DIR", "/app/data")) / "raw"
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(5)
    
    def get_current_query(self):
        if not self.queries:
            return None
        return self.queries[self.query_index % len(self.queries)]
    
    def next_query(self):
        self.query_index += 1
        return self.query_index < len(self.queries)
        
    async def fetch_listings_page(
        self, 
        client: httpx.AsyncClient, 
        query: str,
        cursor: Optional[str] = None,
        retries: int = 3
    ) -> Dict:
        url = f"{self.base_url}/api/v2/searchPropertyByLocation"
        
        params = {
            "query": query,
            "adults": "1",
            "guestFavorite": "false",
            "ib": "false",
            "currency": "USD"
        }
        if cursor:
            params["cursor"] = cursor
        
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    cursor_info = f" (cursor: {cursor[:20]}...)" if cursor else " (first page)"
                    logger.info(f"Fetching listings for query '{query}'{cursor_info} (attempt {attempt + 1})...")
                    
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
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    query_safe = query.replace(" ", "_").replace(",", "")
                    cursor_safe = cursor[:20].replace("/", "_").replace("=", "") if cursor else "first"
                    raw_file = self.raw_data_dir / f"query_{query_safe}_{cursor_safe}.json"
                    with open(raw_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    listings_count = len(self.extract_listings_from_response(data))
                    logger.info(f"Successfully fetched {listings_count} listings for query '{query}'")
                    return data
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error on attempt {attempt + 1}: {e.response.status_code}")
                    if e.response.status_code == 429:
                        wait_time = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Error fetching query '{query}' (attempt {attempt + 1}): {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        raise
        
        return {}
        
    def extract_listings_from_response(self, data: Dict) -> List[Dict]:
        """Extract listings from API response"""
        if "data" in data and "list" in data["data"]:
            return data["data"]["list"]
        elif "list" in data:
            return data["list"]
        return []
    
    async def fetch_all_listings(self, max_listings: int) -> List[Dict]:
        all_listings = []
        seen_ids = set()
        
        async with httpx.AsyncClient() as client:
            while len(all_listings) < max_listings:
                query = self.get_current_query()
                if not query:
                    logger.info("No query specified, stopping API fetching.")
                    break
                
                logger.info(f"Fetching listings for query '{query}' (index {self.query_index})")
                
                cursor = None
                page_count = 0
                max_pages_per_query = 100
                
                while len(all_listings) < max_listings and page_count < max_pages_per_query:
                    try:
                        data = await self.fetch_listings_page(client, query, cursor=cursor)
                        listings = self.extract_listings_from_response(data)
                        
                        if listings:
                            new_listings = []
                            for listing in listings:
                                listing_data = listing.get("listing", listing)
                                listing_id = str(listing_data.get("id", ""))
                                
                                if listing_id and listing_id not in seen_ids and listing_id != "":
                                    seen_ids.add(listing_id)
                                    new_listings.append(listing)
                            
                            all_listings.extend(new_listings)
                            logger.info(f"Fetched {len(new_listings)} new listings from '{query}' page {page_count + 1} (skipped {len(listings) - len(new_listings)} duplicates). Total: {len(all_listings)}/{max_listings}")
                        else:
                            logger.warning(f"No listings in response for query '{query}' page {page_count + 1}")
                        
                        if "data" in data and "nextPageCursor" in data["data"]:
                            cursor = data["data"]["nextPageCursor"]
                            if not cursor:
                                logger.info(f"No more pages for query '{query}' (fetched {page_count + 1} pages)")
                                break
                        else:
                            logger.info(f"No pagination cursor for query '{query}', stopping")
                            break
                        
                        page_count += 1
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error fetching query '{query}' page {page_count + 1}: {e}")
                        break
                
                if len(all_listings) < max_listings:
                    if not self.next_query():
                        logger.info("All queries exhausted, stopping")
                        break
                    await asyncio.sleep(2)
                else:
                    break
        
        logger.info(f"Total unique listings fetched: {len(all_listings)}")
        return all_listings[:max_listings]
