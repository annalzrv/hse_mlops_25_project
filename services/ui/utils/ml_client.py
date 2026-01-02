import os
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MLInferenceClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("ML_INFERENCE_URL", "http://ml_inference:8000")

    def health_check(self) -> Dict:
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def predict_by_listing_id(self, listing_id: str) -> Dict:
        try:
            response = requests.post(
                f"{self.base_url}/predict",
                json={"listing_id": listing_id},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Prediction failed for listing {listing_id}: {e}")
            raise

    def predict_by_data(
        self,
        listing_data: Dict,
        embedding: Optional[List[float]] = None,
        city: Optional[str] = None,
        num_reviews: Optional[int] = None
    ) -> Dict:
        try:
            payload = {
                "listing_data": listing_data,
                "embedding": embedding,
                "city": city,
                "num_reviews": num_reviews
            }
            response = requests.post(
                f"{self.base_url}/predict",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Prediction failed: {e}")
            raise

    def get_predictions(self, limit: int = 100) -> List[Dict]:
        try:
            response = requests.get(
                f"{self.base_url}/predictions",
                params={"limit": limit},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("predictions", [])
        except requests.RequestException as e:
            logger.error(f"Failed to get predictions: {e}")
            return []

    def get_swagger_url(self) -> str:
        return f"{self.base_url}/docs"

    def get_sample_listings(self, limit: int = 20) -> List[Dict]:
        """Get sample listings for dropdown selection"""
        try:
            response = requests.get(
                f"{self.base_url}/listings/sample",
                params={"limit": limit},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("listings", [])
        except requests.RequestException as e:
            logger.error(f"Failed to get sample listings: {e}")
            return []

