import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from predictor import PricePredictor
from database import DatabaseService
from kafka_consumer import KafkaPredictionConsumer

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/models/model.cbm"))
    PREPROCESSOR_PATH = Path(os.getenv("PREPROCESSOR_PATH", "/app/models/preprocessor.pkl"))
    
    try:
        predictor = PricePredictor(str(MODEL_PATH), str(PREPROCESSOR_PATH))
        logger.info("Predictor loaded successfully")
    except Exception as e:
        logger.error(f"Error loading predictor: {e}")
        raise
    
    try:
        db_service = DatabaseService()
        db_service.connect()
        logger.info("Database service connected")
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise
    
    try:
        consumer = KafkaPredictionConsumer(predictor, db_service)
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        if db_service:
            db_service.close()


if __name__ == "__main__":
    main()

