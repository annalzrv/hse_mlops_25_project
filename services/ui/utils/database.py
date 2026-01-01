import psycopg2
import numpy as np
from typing import Dict, Optional
from config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD
)

class DatabaseService:
    def __init__(self):
        self.conn_params = {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "database": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD
        }
        self.connection = None
        
    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.conn_params)
            return True
        except Exception as e:
            return False
    
    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def save_listing(
        self,
        listing_id: str,
        metadata: Dict,
        embedding: np.ndarray
    ):
        if not self.connection:
            if not self.connect():
                return False, "Failed to connect to database"
        
        try:
            if metadata is None:
                return False, "Metadata is None"
            
            if embedding is None:
                return False, "Embedding is None"
            
            cursor = self.connection.cursor()
            
            price = metadata.get("price")
            lat = metadata.get("lat")
            lng = metadata.get("lng")
            name = (metadata.get("name") or "")[:500]
            rating = metadata.get("rating")
            
            try:
                embedding_str = "[" + ",".join(map(str, embedding.tolist())) + "]"
            except Exception as e:
                return False, f"Error converting embedding: {str(e)}"
            
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
            return True, "Listing saved successfully"
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            return False, f"Database error: {str(e)}"
