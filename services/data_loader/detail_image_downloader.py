"""
Detail Image Downloader - Downloads images from detailed API response

Reads data/raw/details/{listing_id}.json files and downloads all images
from the 'images' array to data/images/{listing_id}/
"""

import os
import asyncio
import aiofiles
import httpx
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from dotenv import load_dotenv

try:
    from logger import setup_logger
except ImportError:
    from services.data_loader.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)


class DetailImageDownloader:
    def __init__(self, data_dir: str = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
        
        self.details_dir = self.data_dir / "raw" / "details"
        self.images_dir = self.data_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        self.semaphore = asyncio.Semaphore(20)  # Concurrent downloads
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def download_image(
        self,
        client: httpx.AsyncClient,
        url: str,
        listing_id: str,
        image_idx: int,
        retries: int = 3
    ) -> Optional[str]:
        """Download a single image"""
        if not url or not url.startswith('http'):
            return None
        
        image_path = self.images_dir / listing_id / f"img_{image_idx:02d}.jpg"
        
        async with self.semaphore:
            for attempt in range(retries):
                try:
                    response = await client.get(url, timeout=self.timeout, follow_redirects=True)
                    response.raise_for_status()
                    
                    async with aiofiles.open(image_path, 'wb') as f:
                        await f.write(response.content)
                    
                    return str(image_path)
                    
                except httpx.HTTPStatusError as e:
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                    else:
                        logger.warning(f"Failed to download {url}: {e.response.status_code}")
                        return None
                except Exception as e:
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                    else:
                        logger.warning(f"Error downloading {url}: {e}")
                        return None
        
        return None
    
    def get_images_from_detail(self, detail_file: Path) -> List[str]:
        """Extract image URLs from a detail JSON file"""
        try:
            with open(detail_file, 'r') as f:
                data = json.load(f)
            
            if not data.get("status") or "data" not in data:
                return []
            
            images = data["data"].get("images", [])
            return [img for img in images if img and img.startswith('http')]
        except Exception as e:
            logger.warning(f"Error reading {detail_file}: {e}")
            return []
    
    async def download_listing_images(
        self,
        client: httpx.AsyncClient,
        listing_id: str,
        image_urls: List[str]
    ) -> int:
        """Download all images for a listing, replacing existing ones"""
        listing_dir = self.images_dir / listing_id
        
        # Delete existing images for this listing
        if listing_dir.exists():
            shutil.rmtree(listing_dir)
        
        listing_dir.mkdir(parents=True, exist_ok=True)
        
        # Download all images
        tasks = [
            self.download_image(client, url, listing_id, idx)
            for idx, url in enumerate(image_urls)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        downloaded = sum(1 for r in results if r and not isinstance(r, Exception))
        return downloaded
    
    async def process_all_listings(self, max_listings: int = None) -> Dict[str, int]:
        """Process all detail files and download images"""
        stats = {"listings": 0, "images_downloaded": 0, "failed": 0}
        
        detail_files = list(self.details_dir.glob("*.json"))
        
        if max_listings:
            detail_files = detail_files[:max_listings]
        
        logger.info(f"Processing {len(detail_files)} listings for image download")
        
        async with httpx.AsyncClient() as client:
            for i, detail_file in enumerate(detail_files):
                listing_id = detail_file.stem
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i + 1}/{len(detail_files)} listings processed")
                
                image_urls = self.get_images_from_detail(detail_file)
                
                if not image_urls:
                    stats["failed"] += 1
                    continue
                
                downloaded = await self.download_listing_images(client, listing_id, image_urls)
                
                stats["listings"] += 1
                stats["images_downloaded"] += downloaded
                
                if downloaded == 0:
                    stats["failed"] += 1
        
        logger.info(f"Completed: {stats['listings']} listings, {stats['images_downloaded']} images")
        return stats


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download images from detailed API data")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Data directory path"
    )
    parser.add_argument(
        "--max-listings",
        type=int,
        default=None,
        help="Maximum listings to process (default: all)"
    )
    
    args = parser.parse_args()
    
    downloader = DetailImageDownloader(data_dir=args.data_dir)
    stats = await downloader.process_all_listings(max_listings=args.max_listings)
    
    print("\n" + "=" * 50)
    print("IMAGE DOWNLOAD COMPLETE")
    print("=" * 50)
    print(f"Listings processed: {stats['listings']}")
    print(f"Images downloaded:  {stats['images_downloaded']}")
    print(f"Failed listings:    {stats['failed']}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

