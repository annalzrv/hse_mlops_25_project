import os
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from preprocessing import Preprocessor
from feature_extractor import prepare_features_from_listing
import logging

logger = logging.getLogger(__name__)


class PricePredictor:
    def __init__(self, model_path: str, preprocessor_path: str):
        self.model_path = Path(model_path)
        self.preprocessor_path = Path(preprocessor_path)
        self.model = None
        self.preprocessor = None
        self.model_version = "v3.0"
        self._load_model()
        self._load_preprocessor()
    
    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        try:
            self.model = CatBoostRegressor()
            self.model.load_model(str(self.model_path))
            logger.info(f"Model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def _load_preprocessor(self):
        if not self.preprocessor_path.exists():
            raise FileNotFoundError(f"Preprocessor file not found: {self.preprocessor_path}")
        
        try:
            self.preprocessor = Preprocessor.load(str(self.preprocessor_path))
            logger.info(f"Preprocessor loaded from {self.preprocessor_path}")
        except Exception as e:
            logger.error(f"Error loading preprocessor: {e}")
            raise
    
    def predict(
        self,
        listing_data: Dict,
        embedding: Optional[np.ndarray] = None,
        city: Optional[str] = None,
        num_reviews: Optional[int] = None,
        amenities: Optional[set] = None
    ) -> float:
        features_df = prepare_features_from_listing(
            listing_data,
            embedding=embedding,
            city=city,
            num_reviews=num_reviews,
            amenities=amenities
        )
        
        try:
            features_transformed = self.preprocessor.transform(features_df)
            prediction = self.model.predict(features_transformed)
            return float(prediction[0])
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            raise
    
    def get_model_version(self) -> str:
        return self.model_version

