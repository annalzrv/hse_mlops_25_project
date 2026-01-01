import streamlit as st
import pandas as pd
from datetime import datetime
from utils.ml_client import MLInferenceClient
from utils.database import DatabaseService
from utils.formatters import format_price

st.set_page_config(page_title="Predictions History", page_icon="scroll", layout="wide")

st.title("Predictions History")
st.markdown("View history of price predictions")

if 'ml_client' not in st.session_state:
    st.session_state.ml_client = MLInferenceClient()

if 'database' not in st.session_state:
    st.session_state.database = DatabaseService()

st.sidebar.header("Filters")
limit = st.sidebar.slider("Number of records", min_value=10, max_value=500, value=100)

col1, col2 = st.sidebar.columns(2)
with col1:
    min_price = st.number_input("Min Price ($)", min_value=0.0, value=0.0, step=10.0)
with col2:
    max_price = st.number_input("Max Price ($)", min_value=0.0, value=10000.0, step=10.0)

if st.button("Refresh Data", use_container_width=True):
    st.rerun()

with st.spinner("Loading predictions..."):
    predictions = st.session_state.ml_client.get_predictions(limit=limit)

if predictions:
    df = pd.DataFrame(predictions)
    
    if 'predicted_price' in df.columns:
        df = df[(df['predicted_price'] >= min_price) & (df['predicted_price'] <= max_price)]
    
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
        df = df.sort_values('created_at', ascending=False)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Predictions", len(df))
    with col2:
        if 'predicted_price' in df.columns and len(df) > 0:
            st.metric("Avg Price", format_price(df['predicted_price'].mean()))
        else:
            st.metric("Avg Price", "N/A")
    with col3:
        if 'predicted_price' in df.columns and len(df) > 0:
            st.metric("Min Price", format_price(df['predicted_price'].min()))
        else:
            st.metric("Min Price", "N/A")
    with col4:
        if 'predicted_price' in df.columns and len(df) > 0:
            st.metric("Max Price", format_price(df['predicted_price'].max()))
        else:
            st.metric("Max Price", "N/A")
    
    st.markdown("---")
    
    if 'predicted_price' in df.columns:
        df['predicted_price_formatted'] = df['predicted_price'].apply(format_price)
    
    display_cols = ['id', 'listing_id', 'predicted_price_formatted', 'created_at', 'model_version']
    display_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[display_cols] if display_cols else df,
        use_container_width=True,
        hide_index=True
    )
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.info("No predictions found. Make some predictions first!")
    st.markdown("Go to the **Predict Price** page to make predictions.")
