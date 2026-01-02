"""
Detail Parser - Parses fetched property details and updates the database

Reads JSON files from data/raw/details/ and updates listings table with:
- Property metadata (type, capacity, bedrooms, bathrooms)
- Ratings (cleanliness, location, value, etc.)
- Description

Also populates the listing_amenities table.
"""

import os
import re
import json
import psycopg2
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

try:
    from logger import setup_logger
except ImportError:
    from services.data_loader.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)


class DetailParser:
    def __init__(self, data_dir: str = None, db_host: str = "localhost", db_port: str = "5433"):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
        
        self.details_dir = self.data_dir / "raw" / "details"
        
        self.conn_params = {
            "host": db_host,
            "port": db_port,
            "database": os.getenv("POSTGRES_DB", "real_estate"),
            "user": os.getenv("POSTGRES_USER", "mlops"),
            "password": os.getenv("POSTGRES_PASSWORD", "mlops123")
        }
        self.connection = None
    
    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(**self.conn_params)
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")
    
    def parse_beds_baths_from_title(self, title: str) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        """
        Parse bedrooms, beds, and bathrooms from title string.
        Example: "Rental unit in New York · ★4.90 · Studio · 1 bed · 1 shared bath"
        """
        bedrooms = None
        beds = None
        bathrooms = None
        
        if not title:
            return bedrooms, beds, bathrooms
        
        # Parse bedrooms (e.g., "2 bedrooms", "Studio")
        bedroom_match = re.search(r'(\d+)\s*bedroom', title, re.IGNORECASE)
        if bedroom_match:
            bedrooms = int(bedroom_match.group(1))
        elif 'studio' in title.lower():
            bedrooms = 0
        
        # Parse beds (e.g., "1 bed", "2 beds")
        bed_match = re.search(r'(\d+)\s*bed(?!room)', title, re.IGNORECASE)
        if bed_match:
            beds = int(bed_match.group(1))
        
        # Parse bathrooms (e.g., "1 bath", "1.5 baths", "1 shared bath")
        bath_match = re.search(r'([\d.]+)\s*(?:shared\s+)?bath', title, re.IGNORECASE)
        if bath_match:
            bathrooms = float(bath_match.group(1))
        
        return bedrooms, beds, bathrooms
    
    def extract_amenities(self, data: Dict) -> List[Tuple[str, str]]:
        """
        Extract amenities from the details section.
        Returns list of (amenity_name, category) tuples.
        """
        amenities = []
        
        details = data.get("details", [])
        if len(details) < 2:
            return amenities
        
        amenities_section = details[1] if isinstance(details[1], dict) else {}
        amenity_categories = amenities_section.get("amenities", [])
        
        for category in amenity_categories:
            if not isinstance(category, dict):
                continue
            
            category_name = category.get("title", "Other")
            category_amenities = category.get("amenities", [])
            
            for amenity in category_amenities:
                if isinstance(amenity, dict):
                    amenity_name = amenity.get("title", "")
                else:
                    amenity_name = str(amenity)
                
                if amenity_name:
                    amenities.append((amenity_name, category_name))
        
        return amenities
    
    def parse_detail_file(self, filepath: Path) -> Optional[Dict]:
        """Parse a single detail JSON file and extract relevant fields."""
        try:
            with open(filepath, 'r') as f:
                raw_data = json.load(f)
            
            if not raw_data.get("status") or "data" not in raw_data:
                logger.warning(f"Invalid data structure in {filepath}")
                return None
            
            data = raw_data["data"]
            listing_id = filepath.stem
            
            # Parse beds/baths from title
            title = data.get("title", "")
            bedrooms, beds, bathrooms = self.parse_beds_baths_from_title(title)
            
            # Extract main fields
            parsed = {
                "listing_id": listing_id,
                "city": data.get("location"),  # e.g., "New York", "Los Angeles"
                "property_type": data.get("propertyType"),
                "room_type": data.get("roomType"),
                "person_capacity": data.get("personCapacity"),
                "bedrooms": bedrooms,
                "beds": beds,
                "bathrooms": bathrooms,
                "cleanliness_rating": data.get("cleanlinessRating"),
                "location_rating": data.get("locationRating"),
                "value_rating": data.get("valueRating"),
                "communication_rating": data.get("communicationRating"),
                "checkin_rating": data.get("checkinRating"),
                "accuracy_rating": data.get("accuracyRating"),
                "review_count": None,
                "description": None,
                "amenities": self.extract_amenities(data)
            }
            
            # Parse review count
            visible_reviews = data.get("visibleReviewCount")
            if visible_reviews:
                try:
                    parsed["review_count"] = int(visible_reviews)
                except (ValueError, TypeError):
                    pass
            
            # Extract description if available
            default_desc = data.get("defaultDescription", {})
            if isinstance(default_desc, dict):
                parsed["description"] = default_desc.get("htmlDescription") or default_desc.get("description")
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            return None
    
    def update_listing(self, parsed: Dict) -> bool:
        """Update a listing in the database with parsed details."""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Update listings table (including city from location field)
            update_query = """
                UPDATE listings SET
                    property_type = %s,
                    room_type = %s,
                    person_capacity = %s,
                    bedrooms = %s,
                    beds = %s,
                    bathrooms = %s,
                    cleanliness_rating = %s,
                    location_rating = %s,
                    value_rating = %s,
                    communication_rating = %s,
                    checkin_rating = %s,
                    accuracy_rating = %s,
                    review_count = %s,
                    description = %s,
                    details_fetched_at = %s
                WHERE id = %s
            """
            
            # Also update city if we have it from detailed data
            if parsed.get("city"):
                update_query = """
                    UPDATE listings SET
                        city = %s,
                        property_type = %s,
                        room_type = %s,
                        person_capacity = %s,
                        bedrooms = %s,
                        beds = %s,
                        bathrooms = %s,
                        cleanliness_rating = %s,
                        location_rating = %s,
                        value_rating = %s,
                        communication_rating = %s,
                        checkin_rating = %s,
                        accuracy_rating = %s,
                        review_count = %s,
                        description = %s,
                        details_fetched_at = %s
                    WHERE id = %s
                """
                cursor.execute(update_query, (
                    parsed["city"],
                    parsed["property_type"],
                    parsed["room_type"],
                    parsed["person_capacity"],
                    parsed["bedrooms"],
                    parsed["beds"],
                    parsed["bathrooms"],
                    parsed["cleanliness_rating"],
                    parsed["location_rating"],
                    parsed["value_rating"],
                    parsed["communication_rating"],
                    parsed["checkin_rating"],
                    parsed["accuracy_rating"],
                    parsed["review_count"],
                    parsed["description"],
                    datetime.now(),
                    parsed["listing_id"]
                ))
            else:
                cursor.execute(update_query, (
                    parsed["property_type"],
                    parsed["room_type"],
                    parsed["person_capacity"],
                    parsed["bedrooms"],
                    parsed["beds"],
                    parsed["bathrooms"],
                    parsed["cleanliness_rating"],
                    parsed["location_rating"],
                    parsed["value_rating"],
                    parsed["communication_rating"],
                    parsed["checkin_rating"],
                    parsed["accuracy_rating"],
                    parsed["review_count"],
                    parsed["description"],
                    datetime.now(),
                    parsed["listing_id"]
                ))
            
            # Insert amenities
            if parsed["amenities"]:
                # Delete existing amenities first
                cursor.execute(
                    "DELETE FROM listing_amenities WHERE listing_id = %s",
                    (parsed["listing_id"],)
                )
                
                # Insert new amenities
                insert_query = """
                    INSERT INTO listing_amenities (listing_id, amenity_name, amenity_category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (listing_id, amenity_name) DO NOTHING
                """
                
                for amenity_name, category in parsed["amenities"]:
                    cursor.execute(insert_query, (
                        parsed["listing_id"],
                        amenity_name[:200],  # Truncate to fit column
                        category[:100] if category else None
                    ))
            
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating listing {parsed['listing_id']}: {e}")
            self.connection.rollback()
            return False
    
    def process_all_details(self) -> Dict[str, int]:
        """Process all detail files and update the database."""
        stats = {"success": 0, "failed": 0, "skipped": 0}
        
        detail_files = list(self.details_dir.glob("*.json"))
        logger.info(f"Found {len(detail_files)} detail files to process")
        
        if not detail_files:
            logger.warning("No detail files found")
            return stats
        
        self.connect()
        
        try:
            for i, filepath in enumerate(detail_files):
                if (i + 1) % 100 == 0:
                    logger.info(f"Progress: {i + 1}/{len(detail_files)} processed")
                
                parsed = self.parse_detail_file(filepath)
                
                if parsed is None:
                    stats["skipped"] += 1
                    continue
                
                if self.update_listing(parsed):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
        
        finally:
            self.close()
        
        logger.info(f"Completed: {stats['success']} success, {stats['failed']} failed, {stats['skipped']} skipped")
        return stats


def main():
    """Main entry point for detail parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse property details and update database")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Data directory path (default: uses DATA_DIR env var or /app/data)"
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
    
    parser_instance = DetailParser(
        data_dir=args.data_dir,
        db_host=args.db_host,
        db_port=args.db_port
    )
    
    stats = parser_instance.process_all_details()
    
    print("\n" + "=" * 50)
    print("DETAIL PARSING COMPLETE")
    print("=" * 50)
    print(f"Success: {stats['success']}")
    print(f"Failed:  {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")
    print("=" * 50)


if __name__ == "__main__":
    main()

