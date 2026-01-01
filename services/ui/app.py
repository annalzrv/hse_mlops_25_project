import streamlit as st
from utils.ml_client import MLInferenceClient

st.set_page_config(
    page_title="Real Estate Price Prediction",
    page_icon="house",
    layout="wide"
)

if 'ml_client' not in st.session_state:
    st.session_state.ml_client = MLInferenceClient()

st.title("Real Estate Price Prediction System")

st.markdown("""
Welcome to the **Multimodal Real Estate Price Prediction** system.
This MLOps platform predicts rental prices based on property images and metadata.
""")

st.markdown("---")

st.header("Navigation")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("Predict Price")
    st.markdown("Get instant price predictions")
    st.page_link("pages/1_predict.py", label="Go to Predictions")

with col2:
    st.subheader("History")
    st.markdown("View past predictions")
    st.page_link("pages/2_history.py", label="View History")

with col3:
    st.subheader("Analytics")
    st.markdown("Analyze data with charts")
    st.page_link("pages/3_analytics.py", label="Open Analytics")

with col4:
    st.subheader("API Docs")
    st.markdown("REST API documentation")
    st.page_link("pages/4_api.py", label="API Docs")

st.markdown("---")

st.header("System Status")

health = st.session_state.ml_client.health_check()
col1, col2, col3 = st.columns(3)

with col1:
    if health.get("status") == "healthy":
        st.success("ML Service: Online")
    else:
        st.error("ML Service: Offline")

with col2:
    if health.get("model_loaded"):
        st.success("Model: Loaded")
    else:
        st.warning("Model: Not loaded")

with col3:
    st.info("Database: PostgreSQL")

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown("""
**Multimodal Real Estate Price Prediction**

Predicts rental prices using:
- Property images (CLIP embeddings)
- Location data
- Property metadata

Built with FastAPI, Kafka, PostgreSQL, and Streamlit.
""")
