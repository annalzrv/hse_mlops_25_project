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
    
    def get_listings_stats(self):
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating IS NOT NULL THEN 1 END) as with_rating
                FROM listings
                WHERE price IS NOT NULL
            """)
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    'total': row[0],
                    'avg_price': row[1],
                    'min_price': row[2],
                    'max_price': row[3],
                    'avg_rating': row[4],
                    'with_rating': row[5]
                }
            return None
        except Exception:
            return None
    
    def get_listings_price_distribution(self):
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT price FROM listings WHERE price IS NOT NULL ORDER BY price
            """)
            rows = cursor.fetchall()
            cursor.close()
            return [r[0] for r in rows]
        except Exception:
            return []
    
    def get_listings_by_rating(self):
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN rating >= 4.5 THEN '4.5-5.0'
                        WHEN rating >= 4.0 THEN '4.0-4.5'
                        WHEN rating >= 3.5 THEN '3.5-4.0'
                        WHEN rating >= 3.0 THEN '3.0-3.5'
                        ELSE 'Below 3.0'
                    END as rating_range,
                    COUNT(*) as count,
                    AVG(price) as avg_price
                FROM listings
                WHERE rating IS NOT NULL AND price IS NOT NULL
                GROUP BY rating_range
                ORDER BY rating_range DESC
            """)
            rows = cursor.fetchall()
            cursor.close()
            return [{'rating_range': r[0], 'count': r[1], 'avg_price': r[2]} for r in rows]
        except Exception:
            return []
