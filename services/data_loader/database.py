import os
import psycopg2
import numpy as np
from typing import Dict, Optional
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)

class DatabaseService:
    def __init__(self):
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "database": os.getenv("POSTGRES_DB", "real_estate"),
            "user": os.getenv("POSTGRES_USER", "mlops"),
            "password": os.getenv("POSTGRES_PASSWORD", "mlops123")
        }
        self.connection = None
        
    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.conn_params)
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def get_existing_ids(self) -> set:
        """Get set of all existing listing IDs from database"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT id FROM listings")
            existing_ids = {str(row[0]) for row in cursor.fetchall()}
            cursor.close()
            logger.info(f"Loaded {len(existing_ids)} existing listing IDs from database")
            return existing_ids
        except Exception as e:
            logger.error(f"Error getting existing IDs: {e}")
            return set()
    
    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")
    
    def save_listing(
        self,
        listing_id: str,
        metadata: Dict,
        embedding: np.ndarray
    ) -> bool:
        if not self.connection:
            self.connect()
        
        try:
            if metadata is None:
                logger.error(f"Metadata is None for listing {listing_id}")
                return False
            
            if embedding is None:
                logger.error(f"Embedding is None for listing {listing_id}")
                return False
            
            cursor = self.connection.cursor()
            
            price = metadata.get("price")
            lat = metadata.get("lat")
            lng = metadata.get("lng")
            name = (metadata.get("name") or "")[:500]
            rating = metadata.get("rating")
            
            try:
                embedding_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
            except Exception as e:
                logger.error(f"Error converting embedding to string for listing {listing_id}: {e}")
                logger.error(f"Embedding type: {type(embedding)}, shape: {embedding.shape if hasattr(embedding, 'shape') else 'no shape'}")
                return False
            
            query = """
                INSERT INTO listings (id, price, lat, lng, name, rating, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (id) DO UPDATE SET
                    price = EXCLUDED.price,
                    lat = EXCLUDED.lat,
                    lng = EXCLUDED.lng,
                    name = EXCLUDED.name,
                    rating = EXCLUDED.rating,
                    embedding = EXCLUDED.embedding
            """
            
            cursor.execute(query, (listing_id, price, lat, lng, name, rating, embedding_str))
            self.connection.commit()
            cursor.close()
            
            logger.debug(f"Saved listing {listing_id} to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving listing {listing_id}: {e}")
            self.connection.rollback()
            return False

