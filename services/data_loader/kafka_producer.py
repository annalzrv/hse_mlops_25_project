import os
import json
import numpy as np
from datetime import datetime
from confluent_kafka import Producer
from dotenv import load_dotenv
from logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)

class KafkaProducerService:
    def __init__(self):
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.topic = os.getenv("KAFKA_TOPIC", "new_listings")

        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'airbnb-data-loader'
        })
        logger.info(f"Kafka producer initialized for topic: {self.topic}")

    def send_listing(self, listing_id: str, embedding: np.ndarray) -> bool:
        try:
            message = {
                "listing_id": listing_id,
                "embedding": embedding.tolist(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            self.producer.produce(
                self.topic,
                value=json.dumps(message).encode('utf-8'),
                callback=self._delivery_callback
            )

            self.producer.poll(0)
            logger.debug(f"Sent listing {listing_id} to Kafka")
            return True

        except Exception as e:
            logger.error(f"Error sending listing {listing_id} to Kafka: {e}")
            return False

    def flush(self):
        self.producer.flush()
        logger.info("Kafka producer flushed")

    @staticmethod
    def _delivery_callback(err, msg):
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

