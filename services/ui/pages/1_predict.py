import streamlit as st
import numpy as np
from utils.ml_client import MLInferenceClient
from utils.formatters import format_price

st.title("Predict Price")
st.markdown("Get a price prediction for a real estate listing")

if 'ml_client' not in st.session_state:
    st.session_state.ml_client = MLInferenceClient()

# ImageProcessor is loaded lazily only when user uploads images
# This avoids loading the heavy CLIP model on page load

health = st.session_state.ml_client.health_check()
if health.get("status") == "healthy":
    st.sidebar.success("ML Service: Online")
else:
    st.sidebar.error("ML Service: Offline")

st.header("Option 1: Predict by Listing ID")
col1, col2 = st.columns([3, 1])
with col1:
    listing_id = st.text_input("Enter Listing ID from database", placeholder="e.g., 12345678")
with col2:
    st.write("")
    st.write("")
    predict_by_id = st.button("Predict", key="predict_by_id", use_container_width=True)

if predict_by_id and listing_id:
    with st.spinner("Getting prediction..."):
        try:
            result = st.session_state.ml_client.predict_by_listing_id(listing_id)
            st.success(f"Predicted Price: **{format_price(result.get('predicted_price'))}**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Predicted Price", format_price(result.get('predicted_price')))
            with col2:
                st.metric("Model Version", result.get('model_version', 'N/A'))
        except Exception as e:
            st.error(f"Prediction failed: {str(e)}")

st.markdown("---")

st.header("Option 2: Predict with Custom Data")

with st.form("custom_prediction_form"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        name = st.text_input("Property Name", placeholder="Luxury apartment in downtown")
        rating = st.number_input("Rating", min_value=0.0, max_value=5.0, value=4.0, step=0.1)
    
    with col2:
        lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=40.7128, step=0.0001, format="%.4f")
        lng = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-74.0060, step=0.0001, format="%.4f")
    
    with col3:
        city = st.selectbox("City", ["Unknown", "Manhattan", "Brooklyn", "Queens", "Los Angeles", "Beverly Hills", "Santa Monica"])
        num_reviews = st.number_input("Number of Reviews", min_value=0, value=10)
    
    uploaded_images = st.file_uploader(
        "Upload Property Images (optional)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )
    
    submit = st.form_submit_button("Get Prediction", use_container_width=True, type="primary")

if submit:
    listing_data = {
        "name": name,
        "rating": rating,
        "lat": lat,
        "lng": lng
    }
    
    embedding = None
    if uploaded_images:
        with st.spinner("Loading image processor (first time may take a moment)..."):
            # Lazy load ImageProcessor only when images are uploaded
            if 'image_processor' not in st.session_state:
                try:
                    from utils.image_processor import ImageProcessor
                    st.session_state.image_processor = ImageProcessor()
                except Exception as e:
                    st.warning(f"Could not load image processor: {e}")
                    st.session_state.image_processor = None
        
        if st.session_state.get('image_processor'):
            with st.spinner("Processing images..."):
                try:
                    image_bytes = [f.read() for f in uploaded_images]
                    embedding = st.session_state.image_processor.process_images(image_bytes)
                    embedding = embedding.tolist() if embedding is not None else None
                except Exception as e:
                    st.warning(f"Image processing failed: {e}")
    
    with st.spinner("Getting prediction..."):
        try:
            result = st.session_state.ml_client.predict_by_data(
                listing_data=listing_data,
                embedding=embedding,
                city=city,
                num_reviews=num_reviews
            )
            
            st.success("Prediction Complete!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Predicted Price per Night", format_price(result.get('predicted_price')))
            with col2:
                st.metric("Model Version", result.get('model_version', 'N/A'))
                
        except Exception as e:
            st.error(f"Prediction failed: {str(e)}")

st.sidebar.markdown("---")
st.sidebar.markdown("### API Documentation")
st.sidebar.markdown("[Open Swagger UI](http://localhost:8000/docs)")
