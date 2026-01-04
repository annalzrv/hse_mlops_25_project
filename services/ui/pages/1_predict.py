import streamlit as st
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

# Load sample listings for dropdown
if 'sample_listings' not in st.session_state:
    st.session_state.sample_listings = st.session_state.ml_client.get_sample_listings(limit=30)

st.header("Option 1: Select from Database")

sample_listings = st.session_state.sample_listings
if sample_listings:
    # Create display options
    listing_options = {
        f"{l['name']} | {l['region']} | ${l['price']:.0f}/night": l['id']
        for l in sample_listings
    }

    col1, col2 = st.columns([4, 1])
    with col1:
        selected_display = st.selectbox(
            "Choose a listing from the database",
            options=["-- Select a listing --"] + list(listing_options.keys()),
            key="listing_selector"
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("Refresh List", use_container_width=True):
            st.session_state.sample_listings = st.session_state.ml_client.get_sample_listings(limit=30)
            st.rerun()

    if selected_display != "-- Select a listing --":
        selected_id = listing_options[selected_display]

        if st.button("Get Prediction", key="predict_selected", type="primary", use_container_width=True):
            with st.spinner("Getting prediction..."):
                try:
                    result = st.session_state.ml_client.predict_by_listing_id(selected_id)
                    st.success(f"Predicted Price: **{format_price(result.get('predicted_price'))}**")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Predicted Price", format_price(result.get('predicted_price')))
                    with col2:
                        st.metric("Listing ID", selected_id)
                    with col3:
                        st.metric("Model Version", result.get('model_version', 'N/A'))
                except Exception as e:
                    st.error(f"Prediction failed: {str(e)}")
else:
    st.info("No listings available. Load data first.")

st.markdown("---")

st.header("Option 2: Enter Listing ID Manually")
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

st.header("Option 3: Predict with Custom Data")

# City coordinates mapping
CITY_COORDS = {
    "Manhattan": (40.7831, -73.9712),
    "Brooklyn": (40.6782, -73.9442),
    "Queens": (40.7282, -73.7949),
    "New York (Other)": (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "Beverly Hills": (34.0736, -118.4004),
    "Santa Monica": (34.0195, -118.4912),
    "West Hollywood": (34.0900, -118.3617),
}

with st.form("custom_prediction_form"):
    col1, col2 = st.columns(2)

    with col1:
        city = st.selectbox(
            "City / Area",
            options=list(CITY_COORDS.keys()),
            help="Location affects price significantly"
        )
        rating = st.slider("Rating", min_value=0.0, max_value=5.0, value=4.5, step=0.1)
        num_reviews = st.number_input("Number of Reviews", min_value=0, value=50)

    with col2:
        name = st.text_input(
            "Property Description",
            placeholder="e.g., Luxury apartment with pool near beach",
            help="Keywords like 'luxury', 'pool', 'beach', 'parking' affect price"
        )

        st.markdown("**Property Features** (extracted from description)")
        feat_col1, feat_col2 = st.columns(2)
        with feat_col1:
            has_luxury = st.checkbox("Luxury/Premium", value=False)
            has_pool = st.checkbox("Pool", value=False)
        with feat_col2:
            has_beach = st.checkbox("Beach Access", value=False)
            has_parking = st.checkbox("Parking", value=False)

    uploaded_images = st.file_uploader(
        "Upload Property Images (optional) - improves prediction accuracy",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )

    submit = st.form_submit_button("Get Prediction", use_container_width=True, type="primary")

    # Process form submission inside form context where all variables are available
    if submit:
        # Get coordinates from city
        lat, lng = CITY_COORDS.get(city, (40.7128, -74.0060))

        # Build property name with keywords for feature extraction
        name_parts = [name] if name else []
        if has_luxury:
            name_parts.append("luxury")
        if has_pool:
            name_parts.append("pool")
        if has_beach:
            name_parts.append("beach")
        if has_parking:
            name_parts.append("parking")

        full_name = " ".join(name_parts) if name_parts else "Apartment"

        listing_data = {
            "name": full_name,
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
                        # Read file bytes immediately while files are available
                        # Files from file_uploader can only be read once per form submission
                        image_bytes = []
                        for uploaded_file in uploaded_images:
                            # Read the file content
                            uploaded_file.seek(0)  # Ensure we're at the start
                            file_bytes = uploaded_file.read()
                            image_bytes.append(file_bytes)
                        
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

                # Display result immediately inside form
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
