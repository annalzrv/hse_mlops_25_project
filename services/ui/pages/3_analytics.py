import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ml_client import MLInferenceClient
from utils.database import DatabaseService
from utils.formatters import format_price

st.title("Analytics Dashboard")

if 'ml_client' not in st.session_state:
    st.session_state.ml_client = MLInferenceClient()

if 'database' not in st.session_state:
    st.session_state.database = DatabaseService()

tab1, tab2 = st.tabs(["Predictions Analytics", "Listings Analytics"])

with tab1:
    st.header("Predictions Analytics")
    
    with st.spinner("Loading predictions..."):
        predictions = st.session_state.ml_client.get_predictions(limit=500)
    
    if not predictions:
        st.info("No prediction data available yet. Make some predictions first.")
    else:
        df = pd.DataFrame(predictions)
        
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['date'] = df['created_at'].dt.date
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Predictions", len(df))
        with col2:
            if 'predicted_price' in df.columns:
                st.metric("Average Price", format_price(df['predicted_price'].mean()))
        with col3:
            if 'predicted_price' in df.columns:
                st.metric("Median Price", format_price(df['predicted_price'].median()))
        with col4:
            if 'predicted_price' in df.columns:
                st.metric("Std Dev", format_price(df['predicted_price'].std()))
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Price Distribution")
            if 'predicted_price' in df.columns:
                fig = px.histogram(
                    df, x='predicted_price', nbins=30,
                    title="Distribution of Predicted Prices",
                    labels={'predicted_price': 'Predicted Price ($)'}
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Price Box Plot")
            if 'predicted_price' in df.columns:
                fig = px.box(
                    df, y='predicted_price',
                    title="Price Distribution",
                    labels={'predicted_price': 'Predicted Price ($)'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        if 'date' in df.columns:
            st.subheader("Predictions Over Time")
            daily_stats = df.groupby('date').agg({
                'predicted_price': ['count', 'mean']
            }).reset_index()
            daily_stats.columns = ['date', 'count', 'avg_price']
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.line(daily_stats, x='date', y='count', title="Predictions per Day")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.line(daily_stats, x='date', y='avg_price', title="Average Price per Day")
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Listings Analytics")
    st.markdown("Statistics from the listings database")
    
    with st.spinner("Loading listings data..."):
        stats = st.session_state.database.get_listings_stats()
        prices = st.session_state.database.get_listings_price_distribution()
        by_rating = st.session_state.database.get_listings_by_rating()
    
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Listings", stats.get('total', 0))
        with col2:
            st.metric("Avg Price", format_price(stats.get('avg_price')))
        with col3:
            st.metric("Min Price", format_price(stats.get('min_price')))
        with col4:
            st.metric("Max Price", format_price(stats.get('max_price')))
        
        col1, col2 = st.columns(2)
        with col1:
            avg_rating = stats.get('avg_rating')
            st.metric("Average Rating", f"{avg_rating:.2f}" if avg_rating else "N/A")
        with col2:
            st.metric("Listings with Rating", stats.get('with_rating', 0))
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Actual Price Distribution")
            if prices:
                fig = px.histogram(
                    x=prices, nbins=30,
                    title="Distribution of Actual Prices",
                    labels={'x': 'Price ($)'}
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No price data available")
        
        with col2:
            st.subheader("Listings by Rating")
            if by_rating:
                rating_df = pd.DataFrame(by_rating)
                fig = px.bar(
                    rating_df, x='rating_range', y='count',
                    title="Number of Listings by Rating",
                    labels={'rating_range': 'Rating Range', 'count': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No rating data available")
        
        if by_rating:
            st.subheader("Average Price by Rating")
            rating_df = pd.DataFrame(by_rating)
            fig = px.bar(
                rating_df, x='rating_range', y='avg_price',
                title="Average Price by Rating Range",
                labels={'rating_range': 'Rating Range', 'avg_price': 'Avg Price ($)'}
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No listings data available in the database.")

st.sidebar.header("Info")
st.sidebar.markdown("Analytics data is loaded from PostgreSQL and ML inference service.")
