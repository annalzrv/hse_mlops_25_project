import os
import asyncio
import numpy as np
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api_client import AirbnbAPIClient
from image_downloader import ImageDownloader
from image_processor import ImageProcessor
from database import DatabaseService
from kafka_producer import KafkaProducerService
from logger import setup_logger
import time

load_dotenv()

logger = setup_logger(__name__, log_level=os.getenv("LOG_LEVEL", "INFO"))

class DataIngestionPipeline:
    def __init__(self):
        self.api_client = AirbnbAPIClient()
        self.image_downloader = ImageDownloader()
        self.image_processor = ImageProcessor()
        self.database = DatabaseService()
        self.kafka_producer = KafkaProducerService()
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = None
        
    def extract_listing_data(self, listing: Dict) -> Dict:
        """Extract data from listing (API format: searchPropertyByLocation)"""
        listing_data = listing.get("listing", listing)
        
        listing_id = str(listing_data.get("id", "unknown"))
        
        # Extract price from pricingQuote.structuredStayDisplayPrice.primaryLine.price
        price = None
        if "pricingQuote" in listing:
            price_str = listing.get("pricingQuote", {}).get("structuredStayDisplayPrice", {}).get("primaryLine", {}).get("price")
            if price_str:
                try:
                    price = float(price_str.replace("$", "").replace(",", "").strip())
                except:
                    pass
        
        # Extract coordinates
        coord = listing_data.get("coordinate", listing_data.get("legacyCoordinate", {}))
        lat = coord.get("latitude") if coord else None
        lng = coord.get("longitude") if coord else None
        
        # Extract name
        name = listing_data.get("name", "") or listing_data.get("legacyName", "") or listing_data.get("title", "")
        
        # Extract rating
        rating = None
        rating_str = listing_data.get("avgRatingLocalized", "")
        if rating_str and rating_str != "New":
            try:
                rating = float(rating_str.split()[0])
            except:
                pass
        
        return {
            "listing_id": listing_id,
            "price": price,
            "lat": lat,
            "lng": lng,
            "name": name,
            "rating": rating,
            "listing_obj": listing
        }
    
    async def process_listing(self, listing: Dict) -> bool:
        try:
            # Extract data using universal function
            data = self.extract_listing_data(listing)
            listing_id = data["listing_id"]
            
            logger.info(f"Processing listing {listing_id} ({self.processed_count + self.failed_count + 1})")
            
            # Download images (pass full listing object for flexibility)
            image_paths = await self.image_downloader.download_listing_images(
                data["listing_obj"],
                max_images=int(os.getenv("MAX_IMAGES_PER_LISTING", "20"))
            )
            
            if not image_paths:
                logger.warning(f"No images downloaded for listing {listing_id}")
                aggregated_embedding = np.zeros(512, dtype=np.float32)
            else:
                aggregated_embedding = self.image_processor.process_listing_images(image_paths)
                # Ensure embedding is not None
                if aggregated_embedding is None:
                    logger.warning(f"Image processor returned None embedding, using zero vector")
                    aggregated_embedding = np.zeros(512, dtype=np.float32)
            
            metadata = {
                "price": data["price"],
                "lat": data["lat"],
                "lng": data["lng"],
                "name": data["name"],
                "rating": data["rating"]
            }
            
            db_success = self.database.save_listing(listing_id, metadata, aggregated_embedding)
            kafka_success = self.kafka_producer.send_listing(listing_id, aggregated_embedding)
            
            if db_success:
                self.processed_count += 1
                logger.info(f"Successfully processed listing {listing_id} (Total: {self.processed_count})")
                return True
            else:
                self.failed_count += 1
                logger.error(f"Failed to save listing {listing_id} to database")
                return False
                
        except Exception as e:
            self.failed_count += 1
            logger.error(f"Error processing listing {listing_id}: {e}", exc_info=True)
            return False
    
    def print_statistics(self, total_processed: int):
        """Print statistics every 500 listings"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        rate = total_processed / elapsed_time if elapsed_time > 0 else 0
        
        logger.info("=" * 60)
        logger.info(f"STATISTICS CHECKPOINT (processed {total_processed} listings)")
        logger.info(f"  Successfully processed: {self.processed_count}")
        logger.info(f"  Failed: {self.failed_count}")
        logger.info(f"  Elapsed time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
        logger.info(f"  Processing rate: {rate:.2f} listings/second")
        if self.processed_count > 0:
            logger.info(f"  Success rate: {(self.processed_count/total_processed)*100:.1f}%")
        logger.info("=" * 60)
    
    async def run_pipeline(self, max_listings: int = 240):
        logger.info(f"Starting data ingestion pipeline for {max_listings} listings")
        self.start_time = time.time()
        
        try:
            self.database.connect()
            
            listings = await self.api_client.fetch_all_listings(max_listings=max_listings)
            logger.info(f"Fetched {len(listings)} listings from API")
            
            for idx, listing in enumerate(listings, 1):
                await self.process_listing(listing)
                
                # print statistics every 500 listings
                if idx % 500 == 0:
                    self.print_statistics(idx)
                
                await asyncio.sleep(0.5)
            
            self.kafka_producer.flush()
            
            total_processed = self.processed_count + self.failed_count
            logger.info("=" * 60)
            logger.info("PIPELINE COMPLETED")
            logger.info(f"  Total listings processed: {total_processed}")
            logger.info(f"  Successfully processed: {self.processed_count}")
            logger.info(f"  Failed: {self.failed_count}")
            elapsed_time = time.time() - self.start_time
            logger.info(f"  Total time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
            if self.processed_count > 0:
                logger.info(f"  Average rate: {self.processed_count/elapsed_time:.2f} listings/second")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
        finally:
            self.database.close()

async def main():
    max_listings = int(os.getenv("MAX_LISTINGS", "240"))
    pipeline = DataIngestionPipeline()
    await pipeline.run_pipeline(max_listings=max_listings)

if __name__ == "__main__":
    asyncio.run(main())

