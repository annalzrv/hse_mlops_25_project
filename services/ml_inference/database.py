import os
import psycopg2
import numpy as np
from typing import Dict, Optional, List
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


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
    
    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")
    
    def get_listing(self, listing_id: str) -> Optional[Dict]:
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT id, price, lat, lng, name, rating, embedding FROM listings WHERE id = %s",
                (listing_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            listing_id_db, price, lat, lng, name, rating, embedding = row
            
            listing_data = {
                'id': listing_id_db,
                'price': price,
                'lat': lat,
                'lng': lng,
                'name': name,
                'rating': rating
            }
            
            embedding_array = None
            if embedding is not None:
                if hasattr(embedding, '__array__'):
                    embedding_array = np.array(embedding)
                else:
                    import json
                    embedding_array = np.array(json.loads(str(embedding)))
            
            return {
                'listing': listing_data,
                'embedding': embedding_array
            }
        except Exception as e:
            logger.error(f"Error getting listing {listing_id}: {e}")
            return None
    
    def save_prediction(
        self,
        listing_id: str,
        predicted_price: float,
        model_version: str = "v1.0"
    ) -> bool:
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO predictions (listing_id, predicted_price, model_version)
                VALUES (%s, %s, %s)
                """,
                (listing_id, predicted_price, model_version)
            )
            self.connection.commit()
            cursor.close()
            logger.info(f"Prediction saved for listing {listing_id}: ${predicted_price:.2f}")
            return True
        except Exception as e:
            logger.error(f"Error saving prediction: {e}")
            self.connection.rollback()
            return False
    
    def get_predictions(self, limit: int = 100) -> List[Dict]:
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT id, listing_id, predicted_price, created_at, model_version
                FROM predictions
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            cursor.close()
            
            predictions = []
            for row in rows:
                predictions.append({
                    'id': row[0],
                    'listing_id': row[1],
                    'predicted_price': row[2],
                    'created_at': row[3],
                    'model_version': row[4]
                })
            
            return predictions
        except Exception as e:
            logger.error(f"Error getting predictions: {e}")
            return []

