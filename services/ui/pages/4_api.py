import streamlit as st
from utils.ml_client import MLInferenceClient

st.set_page_config(page_title="API Documentation", page_icon="satellite", layout="wide")

st.title("API Documentation")
st.markdown("Explore the ML Inference API endpoints")

if 'ml_client' not in st.session_state:
    st.session_state.ml_client = MLInferenceClient()

health = st.session_state.ml_client.health_check()
if health.get("status") == "healthy":
    st.success("ML Inference Service is online")
else:
    st.error(f"ML Inference Service is offline: {health.get('error', 'Unknown error')}")

st.markdown("---")

st.header("Interactive API Documentation")

st.markdown("""
The ML Inference Service provides a **Swagger UI** for interactive API documentation.

**[Open Swagger UI](http://localhost:8000/docs)** (opens in new tab)

This allows you to:
- View all available API endpoints
- See request/response schemas
- Test API calls directly from the browser

> Note: Swagger UI is available at `http://localhost:8000/docs` when running locally.
""")

st.markdown("---")

st.header("API Endpoints")

with st.expander("GET /health - Health Check", expanded=True):
    st.markdown("""
    **Description:** Check if the ML service is running and healthy.
    
    **Response:**
    ```json
    {
        "status": "healthy",
        "model_loaded": true
    }
    ```
    """)
    
    if st.button("Test Health Check"):
        result = st.session_state.ml_client.health_check()
        st.json(result)

with st.expander("POST /predict - Make Prediction"):
    st.markdown("""
    **Description:** Get a price prediction for a listing.
    
    **Option 1: By Listing ID**
    ```json
    {
        "listing_id": "12345678"
    }
    ```
    
    **Option 2: With Custom Data**
    ```json
    {
        "listing_data": {
            "name": "Luxury Apartment",
            "rating": 4.5,
            "lat": 40.7128,
            "lng": -74.0060
        },
        "city": "Manhattan",
        "num_reviews": 50,
        "embedding": [0.1, 0.2, ...]
    }
    ```
    
    **Response:**
    ```json
    {
        "predicted_price": 299.99,
        "model_version": "v1.0",
        "listing_id": "12345678"
    }
    ```
    """)

with st.expander("GET /predictions - Get Prediction History"):
    st.markdown("""
    **Description:** Get history of predictions.
    
    **Query Parameters:**
    - `limit` (optional): Maximum number of records (default: 100)
    
    **Response:**
    ```json
    {
        "predictions": [
            {
                "id": 1,
                "listing_id": "12345678",
                "predicted_price": 299.99,
                "created_at": "2025-01-01T12:00:00",
                "model_version": "v1.0"
            }
        ],
        "count": 1
    }
    ```
    """)
    
    limit = st.number_input("Limit", min_value=1, max_value=100, value=5)
    if st.button("Test Get Predictions"):
        predictions = st.session_state.ml_client.get_predictions(limit=limit)
        st.json({"predictions": predictions, "count": len(predictions)})

st.markdown("---")

st.header("Base URL")
st.code(st.session_state.ml_client.base_url)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Links")
st.sidebar.markdown("- [Swagger UI](http://localhost:8000/docs)")
st.sidebar.markdown("- [ReDoc](http://localhost:8000/redoc)")
