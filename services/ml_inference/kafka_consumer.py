import os
import json
import logging
from typing import Optional
from confluent_kafka import Consumer, KafkaError
from dotenv import load_dotenv
from predictor import PricePredictor
from database import DatabaseService

load_dotenv()

logger = logging.getLogger(__name__)


class KafkaPredictionConsumer:
    def __init__(
        self,
        predictor: PricePredictor,
        db_service: DatabaseService,
        topic: str = "new_listings",
        bootstrap_servers: Optional[str] = None
    ):
        self.predictor = predictor
        self.db_service = db_service
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"
        )
        self.consumer = None
        self.running = False

    def _create_consumer(self):
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': 'ml_inference_consumer',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True
        }
        self.consumer = Consumer(config)
        self.consumer.subscribe([self.topic])
        logger.info(f"Kafka consumer created for topic: {self.topic}")

    def start(self):
        self._create_consumer()
        self.running = True
        logger.info("Starting Kafka prediction consumer...")

        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        continue

                try:
                    message_value = msg.value().decode('utf-8')
                    message_data = json.loads(message_value)

                    listing_id = message_data.get('listing_id')
                    if not listing_id:
                        logger.warning("Message missing listing_id, skipping")
                        continue

                    logger.info(f"Processing listing {listing_id}...")

                    listing_result = self.db_service.get_listing(listing_id)
                    if not listing_result:
                        logger.warning(f"Listing {listing_id} not found in database")
                        continue

                    listing_data = listing_result['listing']
                    embedding = listing_result['embedding']

                    predicted_price = self.predictor.predict(
                        listing_data,
                        embedding=embedding
                    )

                    self.db_service.save_prediction(
                        listing_id,
                        predicted_price,
                        self.predictor.get_model_version()
                    )

                    logger.info(f"Prediction for listing {listing_id}: ${predicted_price:.2f}")

                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

