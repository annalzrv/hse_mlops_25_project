import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.ml_client import MLInferenceClient
from utils.database import DatabaseService
from utils.formatters import format_price

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")

st.title("📊 Analytics Dashboard")
st.markdown("Analyze prediction data and trends")

if 'ml_client' not in st.session_state:
    st.session_state.ml_client = MLInferenceClient()

if 'database' not in st.session_state:
    st.session_state.database = DatabaseService()

with st.spinner("Loading data..."):
    predictions = st.session_state.ml_client.get_predictions(limit=500)

if not predictions:
    st.warning("No prediction data available yet.")
    st.info("Make some predictions first using the **Predict Price** page.")
    st.stop()

df = pd.DataFrame(predictions)

if 'created_at' in df.columns:
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['date'] = df['created_at'].dt.date

st.header("Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Predictions", len(df))
with col2:
    if 'predicted_price' in df.columns:
        st.metric("Average Price", format_price(df['predicted_price'].mean()))
    else:
        st.metric("Average Price", "N/A")
with col3:
    if 'predicted_price' in df.columns:
        st.metric("Median Price", format_price(df['predicted_price'].median()))
    else:
        st.metric("Median Price", "N/A")
with col4:
    if 'predicted_price' in df.columns:
        st.metric("Price Std Dev", format_price(df['predicted_price'].std()))
    else:
        st.metric("Price Std Dev", "N/A")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Price Distribution")
    if 'predicted_price' in df.columns:
        fig = px.histogram(
            df,
            x='predicted_price',
            nbins=30,
            title="Distribution of Predicted Prices",
            labels={'predicted_price': 'Predicted Price ($)'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No price data available")

with col2:
    st.subheader("Price Box Plot")
    if 'predicted_price' in df.columns:
        fig = px.box(
            df,
            y='predicted_price',
            title="Price Distribution (Box Plot)",
            labels={'predicted_price': 'Predicted Price ($)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No price data available")

st.markdown("---")

st.subheader("Predictions Over Time")
if 'date' in df.columns:
    daily_stats = df.groupby('date').agg({
        'predicted_price': ['count', 'mean']
    }).reset_index()
    daily_stats.columns = ['date', 'count', 'avg_price']
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.line(
            daily_stats,
            x='date',
            y='count',
            title="Predictions per Day",
            labels={'count': 'Number of Predictions', 'date': 'Date'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.line(
            daily_stats,
            x='date',
            y='avg_price',
            title="Average Predicted Price per Day",
            labels={'avg_price': 'Average Price ($)', 'date': 'Date'}
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No time series data available")

st.markdown("---")

st.subheader("Price Statistics")
if 'predicted_price' in df.columns:
    stats_df = pd.DataFrame({
        'Metric': ['Count', 'Mean', 'Median', 'Std Dev', 'Min', 'Max', '25th Percentile', '75th Percentile'],
        'Value': [
            len(df),
            f"${df['predicted_price'].mean():.2f}",
            f"${df['predicted_price'].median():.2f}",
            f"${df['predicted_price'].std():.2f}",
            f"${df['predicted_price'].min():.2f}",
            f"${df['predicted_price'].max():.2f}",
            f"${df['predicted_price'].quantile(0.25):.2f}",
            f"${df['predicted_price'].quantile(0.75):.2f}"
        ]
    })
    st.table(stats_df)

st.sidebar.header("Data Info")
st.sidebar.metric("Total Records", len(df))
if 'date' in df.columns:
    st.sidebar.metric("Date Range", f"{df['date'].min()} to {df['date'].max()}")
st.sidebar.markdown("---")
st.sidebar.info("Data is loaded from the ML inference service.")

