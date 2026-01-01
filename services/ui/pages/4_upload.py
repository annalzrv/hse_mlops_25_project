import streamlit as st
import numpy as np
from utils.database import DatabaseService
from utils.image_processor import ImageProcessor
from utils.formatters import format_price, format_rating, format_coordinates

st.set_page_config(page_title="Upload Listing", page_icon="📤", layout="wide")

st.title("📤 Upload Listing")
st.markdown("Upload real estate listings with metadata and images")

if 'image_processor' not in st.session_state:
    try:
        with st.spinner("Loading CLIP model..."):
            st.session_state.image_processor = ImageProcessor()
        st.sidebar.success("CLIP model loaded")
    except Exception as e:
        st.sidebar.error(f"CLIP model failed: {str(e)[:50]}")
        st.session_state.image_processor = None

if 'database' not in st.session_state:
    st.session_state.database = DatabaseService()

with st.form("listing_form", clear_on_submit=False):
    st.header("Listing Information")
    
    col1, col2 = st.columns(2)
    
    autofill_listing_id = st.session_state.get('autofill_listing_id', '')
    autofill_name = st.session_state.get('autofill_name', '')
    autofill_price = st.session_state.get('autofill_price', None)
    autofill_lat = st.session_state.get('autofill_lat', None)
    autofill_lng = st.session_state.get('autofill_lng', None)
    autofill_rating = st.session_state.get('autofill_rating', None)
    
    with col1:
        listing_id = st.text_input("Listing ID *", value=autofill_listing_id, placeholder="e.g., 12345678")
        name = st.text_input("Name", value=autofill_name, placeholder="e.g., Beautiful apartment")
        price = st.number_input("Price ($)", min_value=0.0, value=autofill_price, step=1.0)
    
    with col2:
        lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=autofill_lat, step=0.000001, format="%.6f")
        lng = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=autofill_lng, step=0.000001, format="%.6f")
        rating = st.number_input("Rating", min_value=0.0, max_value=5.0, value=autofill_rating, step=0.1)
    
    st.header("Upload Images")
    uploaded_files = st.file_uploader(
        "Select images (JPG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.info(f"Uploaded {len(uploaded_files)} image(s)")
        cols = st.columns(min(3, len(uploaded_files)))
        for idx, uploaded_file in enumerate(uploaded_files[:3]):
            with cols[idx % 3]:
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
    
    col_submit, col_autofill = st.columns([1, 1])
    
    with col_submit:
        submit_button = st.form_submit_button("Save Listing", type="primary", use_container_width=True)
    
    with col_autofill:
        autofill_clicked = st.form_submit_button("Auto-fill (Test)", use_container_width=True)

if autofill_clicked:
    st.session_state.autofill_listing_id = "test_listing_001"
    st.session_state.autofill_name = "Luxury Beachfront Apartment"
    st.session_state.autofill_price = 250.0
    st.session_state.autofill_lat = 34.0522
    st.session_state.autofill_lng = -118.2437
    st.session_state.autofill_rating = 4.5
    st.rerun()

if submit_button:
    if not listing_id:
        st.error("Listing ID is required!")
    else:
        try:
            metadata = {
                "name": name if name else None,
                "price": float(price) if price is not None else None,
                "lat": float(lat) if lat is not None else None,
                "lng": float(lng) if lng is not None else None,
                "rating": float(rating) if rating is not None else None
            }
            
            embedding = None
            if uploaded_files and st.session_state.image_processor:
                try:
                    with st.spinner("Processing images..."):
                        image_bytes_list = [file.read() for file in uploaded_files]
                        embedding = st.session_state.image_processor.process_images(image_bytes_list)
                    if embedding is not None:
                        st.success(f"Processed {len(uploaded_files)} image(s)")
                except Exception as e:
                    st.warning(f"Image processing failed: {str(e)}")
                    embedding = np.zeros(512, dtype=np.float32)
            
            if embedding is None:
                embedding = np.zeros(512, dtype=np.float32)
                st.info("Using zero embedding (no images)")
            
            with st.spinner("Saving to database..."):
                success, message = st.session_state.database.save_listing(
                    listing_id=listing_id,
                    metadata=metadata,
                    embedding=embedding
                )
            
            if success:
                st.success(f"{message}")
                
                st.header("Saved Listing Details")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Listing ID", listing_id)
                    st.metric("Price", format_price(metadata.get("price")))
                
                with col2:
                    st.metric("Rating", format_rating(metadata.get("rating")))
                    st.metric("Coordinates", format_coordinates(metadata.get("lat"), metadata.get("lng")))
                
                with col3:
                    st.metric("Name", metadata.get("name") or "N/A")
                    if embedding is not None:
                        st.metric("Embedding Norm", f"{np.linalg.norm(embedding):.4f}")
            else:
                st.error(f"{message}")
                
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown("Upload listings with metadata and images for price prediction.")

