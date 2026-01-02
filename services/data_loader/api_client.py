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

        place_ids_str = os.getenv("PLACE_ID", "")
        self.place_ids = [pid.strip() for pid in place_ids_str.split(",") if pid.strip()]
        self.place_id_index = 0

        self.base_url = f"https://{self.api_host}"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        self.raw_data_dir = Path(os.getenv("DATA_DIR", "/app/data")) / "raw" / "search"
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(5)

    def get_current_place_id(self):
        if not self.place_ids:
            return None
        return self.place_ids[self.place_id_index % len(self.place_ids)]

    def next_place_id(self):
        self.place_id_index += 1
        return self.place_id_index < len(self.place_ids)

    async def fetch_listings_page(
        self,
        client: httpx.AsyncClient,
        place_id: str,
        cursor: Optional[str] = None,
        retries: int = 3
    ) -> Dict:
        url = f"{self.base_url}/api/v2/searchPropertyByPlaceId"

        params = {
            "placeId": place_id,
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
                    logger.info(f"Fetching listings for place_id '{place_id}'{cursor_info} (attempt {attempt + 1})...")

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

                    place_id_safe = place_id.replace("/", "_").replace("=", "")
                    cursor_safe = cursor[:20].replace("/", "_").replace("=", "") if cursor else "first"
                    raw_file = self.raw_data_dir / f"place_id_{place_id_safe}_{cursor_safe}.json"
                    with open(raw_file, 'w') as f:
                        json.dump(data, f, indent=2)

                    listings_count = len(self.extract_listings_from_response(data))
                    logger.info(f"Successfully fetched {listings_count} listings for place_id '{place_id}'")
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

    async def fetch_all_listings(self, max_listings: int, existing_ids: set = None) -> List[Dict]:
        all_listings = []
        seen_ids = existing_ids.copy() if existing_ids else set()

        async with httpx.AsyncClient() as client:
            while len(all_listings) < max_listings:
                place_id = self.get_current_place_id()
                if not place_id:
                    logger.info("No place_id specified, stopping API fetching.")
                    break

                logger.info(f"Fetching listings for place_id '{place_id}' (index {self.place_id_index})")

                cursor = None
                page_count = 0
                max_pages_per_place_id = 100
                consecutive_empty_pages = 0
                max_consecutive_empty = 10
                cursor_not_changing_count = 0
                max_cursor_not_changing = 3

                while len(all_listings) < max_listings and page_count < max_pages_per_place_id:
                    try:
                        data = await self.fetch_listings_page(client, place_id, cursor=cursor)
                        listings = self.extract_listings_from_response(data)

                        if listings:
                            page_listing_ids = []
                            new_listings = []
                            for listing in listings:
                                listing_data = listing.get("listing", listing)
                                listing_id = str(listing_data.get("id", ""))
                                page_listing_ids.append(listing_id)

                                if listing_id and listing_id not in seen_ids and listing_id != "":
                                    seen_ids.add(listing_id)
                                    new_listings.append(listing)

                            cursor_preview = cursor[:50] + "..." if cursor and len(cursor) > 50 else (cursor or "None")
                            sample_ids = page_listing_ids[:5]
                            logger.info(f"Page {page_count + 1} | Cursor: {cursor_preview} | Total in seen_ids: {len(seen_ids)} | Sample listing_ids: {sample_ids}")

                            if len(new_listings) > 0:
                                consecutive_empty_pages = 0
                            else:
                                consecutive_empty_pages += 1

                            all_listings.extend(new_listings)
                            logger.info(f"Fetched {len(new_listings)} new listings from place_id '{place_id}' page {page_count + 1} (skipped {len(listings) - len(new_listings)} duplicates). Total: {len(all_listings)}/{max_listings} (consecutive_empty: {consecutive_empty_pages})")

                            if consecutive_empty_pages >= max_consecutive_empty:
                                logger.info(f"Found {max_consecutive_empty} consecutive pages with no new listings for place_id '{place_id}', moving to next place_id")
                                break
                        else:
                            consecutive_empty_pages += 1
                            logger.warning(f"No listings in response for place_id '{place_id}' page {page_count + 1}")

                            if consecutive_empty_pages >= max_consecutive_empty:
                                logger.info(f"Found {max_consecutive_empty} consecutive empty pages for place_id '{place_id}', moving to next place_id")
                                break

                        if "data" in data and "nextPageCursor" in data["data"]:
                            old_cursor = cursor
                            new_cursor = data["data"]["nextPageCursor"]
                            if not new_cursor:
                                logger.info(f"No more pages for place_id '{place_id}' (fetched {page_count + 1} pages)")
                                break

                            if old_cursor == new_cursor:
                                cursor_not_changing_count += 1
                                logger.warning(f"Cursor did not change for place_id '{place_id}' page {page_count + 1} (count: {cursor_not_changing_count}/{max_cursor_not_changing}). API keeps returning same cursor.")
                                if cursor_not_changing_count >= max_cursor_not_changing:
                                    logger.warning(f"Cursor did not change {max_cursor_not_changing} times in a row. API pagination seems broken for this place_id. Stopping pagination.")
                                    break
                            else:
                                cursor_not_changing_count = 0

                            cursor = new_cursor
                        else:
                            logger.info(f"No pagination cursor for place_id '{place_id}', stopping")
                            break

                        page_count += 1
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"Error fetching place_id '{place_id}' page {page_count + 1}: {e}")
                        break

                if len(all_listings) < max_listings:
                    if not self.next_place_id():
                        logger.info("All place_ids exhausted, stopping")
                        break
                    await asyncio.sleep(2)
                else:
                    break

        logger.info(f"Total unique listings fetched: {len(all_listings)}")
        return all_listings[:max_listings]
