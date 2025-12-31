import os
import asyncio
import aiofiles
import httpx
from pathlib import Path
from typing import List, Optional
from logger import setup_logger

logger = setup_logger(__name__)

class ImageDownloader:
    def __init__(self):
        self.images_dir = Path(os.getenv("DATA_DIR", "/app/data")) / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(50)
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        
    async def download_image(
        self,
        client: httpx.AsyncClient,
        url: str,
        listing_id: str,
        image_id: str,
        retries: int = 3
    ) -> Optional[str]:
        if not url or not url.startswith('http'):
            return None
            
        image_path = self.images_dir / listing_id / f"{image_id}.jpg"
        
        if image_path.exists():
            logger.debug(f"Image already exists: {image_path}")
            return str(image_path)
        
        image_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    response = await client.get(url, timeout=self.timeout, follow_redirects=True)
                    response.raise_for_status()
                    
                    async with aiofiles.open(image_path, 'wb') as f:
                        await f.write(response.content)
                    
                    logger.debug(f"Downloaded image: {image_path}")
                    return str(image_path)
                    
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error downloading {url} (attempt {attempt + 1}): {e.response.status_code}")
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                    else:
                        return None
                except Exception as e:
                    logger.warning(f"Error downloading {url} (attempt {attempt + 1}): {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                    else:
                        return None
        
        return None
    
    async def download_listing_images(
        self,
        listing: dict,
        max_images: int = 20
    ) -> List[str]:
        """Download images from listing (API format: searchPropertyByLocation)"""
        listing_data = listing.get("listing", listing)
        listing_id = str(listing_data.get("id", "unknown"))
        image_urls = []
        
        # Format: contextualPictures in listing_data
        if "contextualPictures" in listing_data and isinstance(listing_data["contextualPictures"], list):
            image_urls = [pic.get("picture") for pic in listing_data["contextualPictures"][:max_images] if pic.get("picture")]
        
        if not image_urls:
            logger.warning(f"No images found for listing {listing_id}")
            return []
        
        downloaded_paths = []
        
        async with httpx.AsyncClient() as client:
            tasks = [
                self.download_image(client, url, listing_id, f"img_{i}")
                for i, url in enumerate(image_urls)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in image download task: {result}")
                elif result:
                    downloaded_paths.append(result)
        
        logger.info(f"Downloaded {len(downloaded_paths)}/{len(image_urls)} images for listing {listing_id}")
        return downloaded_paths

