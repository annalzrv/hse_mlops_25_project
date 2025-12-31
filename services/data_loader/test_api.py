import asyncio
import os
from dotenv import load_dotenv
from api_client import AirbnbAPIClient
from logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)

async def test_api():
    client = AirbnbAPIClient()
    
    logger.info("Testing API connection...")
    logger.info(f"API Host: {client.api_host}")
    logger.info(f"Place ID: {client.place_id}")
    
    try:
        import httpx
        async with httpx.AsyncClient() as http_client:
            data = await client.fetch_listings_page(http_client, cursor=None)
            
            logger.info("API Response Structure:")
            logger.info(f"Top-level keys: {list(data.keys())}")
            
            if "data" in data:
                logger.info(f"Data keys: {list(data['data'].keys())}")
                if "list" in data["data"]:
                    listings = data["data"]["list"]
                    logger.info(f"Number of listings: {len(listings)}")
                    if listings:
                        logger.info(f"First listing keys: {list(listings[0].keys())}")
                        logger.info(f"First listing ID: {listings[0].get('id')}")
                        logger.info(f"First listing name: {listings[0].get('name', 'N/A')[:50]}")
                        
                        if "images" in listings[0]:
                            logger.info(f"Images in first listing: {len(listings[0]['images'])}")
                        elif "pictureUrl" in listings[0]:
                            logger.info(f"Picture URL: {listings[0]['pictureUrl']}")
                
                cursor = data.get("data", {}).get("nextPageCursor")
                logger.info(f"Next page cursor: {cursor[:50] if cursor else 'None'}...")
            
            logger.info("API test successful!")
            return True
            
    except Exception as e:
        logger.error(f"API test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_api())

