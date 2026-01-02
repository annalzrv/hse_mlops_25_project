import os
import logging
from pathlib import Path
from typing import Optional, Dict
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from predictor import PricePredictor
from database import DatabaseService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Real Estate Price Prediction API",
    description="ML inference service for predicting real estate prices",
    version="1.0.0"
)

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/models/model.cbm"))
PREPROCESSOR_PATH = Path(os.getenv("PREPROCESSOR_PATH", "/app/models/preprocessor.pkl"))

predictor: Optional[PricePredictor] = None
db_service: Optional[DatabaseService] = None


@app.on_event("startup")
async def startup_event():
    global predictor, db_service

    try:
        predictor = PricePredictor(
            str(MODEL_PATH),
            str(PREPROCESSOR_PATH)
        )
        logger.info("Predictor initialized")
    except Exception as e:
        logger.error(f"Error initializing predictor: {e}")
        raise

    try:
        db_service = DatabaseService()
        db_service.connect()
        logger.info("Database service initialized")
    except Exception as e:
        logger.error(f"Error initializing database service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    global db_service
    if db_service:
        db_service.close()


class PredictionRequest(BaseModel):
    listing_id: Optional[str] = None
    listing_data: Optional[Dict] = None
    embedding: Optional[list] = None
    city: Optional[str] = None
    num_reviews: Optional[int] = None


class PredictionResponse(BaseModel):
    predicted_price: float
    model_version: str
    listing_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": predictor is not None}


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    if not predictor:
        raise HTTPException(status_code=503, detail="Predictor not initialized")

    try:
        if request.listing_id:
            if not db_service:
                raise HTTPException(status_code=503, detail="Database service not initialized")

            listing_result = db_service.get_listing(request.listing_id)
            if not listing_result:
                raise HTTPException(status_code=404, detail=f"Listing {request.listing_id} not found")

            listing_data = listing_result['listing']
            embedding = listing_result['embedding']
            amenities = listing_result.get('amenities', set())

            predicted_price = predictor.predict(
                listing_data,
                embedding=embedding,
                amenities=amenities
            )

            if db_service:
                db_service.save_prediction(
                    request.listing_id,
                    predicted_price,
                    predictor.get_model_version()
                )

            return PredictionResponse(
                predicted_price=predicted_price,
                model_version=predictor.get_model_version(),
                listing_id=request.listing_id
            )
        elif request.listing_data:
            embedding_array = None
            if request.embedding:
                embedding_array = np.array(request.embedding)

            predicted_price = predictor.predict(
                request.listing_data,
                embedding=embedding_array,
                city=request.city,
                num_reviews=request.num_reviews
            )

            return PredictionResponse(
                predicted_price=predicted_price,
                model_version=predictor.get_model_version(),
                listing_id=None
            )
        else:
            raise HTTPException(status_code=400, detail="Either listing_id or listing_data must be provided")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/predictions")
async def get_predictions(limit: int = 100):
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")

    try:
        predictions = db_service.get_predictions(limit=limit)
        return {"predictions": predictions, "count": len(predictions)}
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting predictions: {str(e)}")


@app.get("/listings/sample")
async def get_sample_listings(limit: int = 20):
    """Get sample listings for UI dropdown selection"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")

    try:
        listings = db_service.get_sample_listings(limit=limit)
        return {"listings": listings, "count": len(listings)}
    except Exception as e:
        logger.error(f"Error getting sample listings: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting sample listings: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

