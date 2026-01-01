import os
import sys
import psycopg2
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List
import json

load_dotenv()

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "real_estate"),
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops123")
    )
    return conn

def extract_embedding_features(embedding_array: np.ndarray) -> Dict[str, float]:
    if embedding_array is None or len(embedding_array) == 0:
        return {}
    
    features = {}
    for i in range(min(512, len(embedding_array))):
        features[f'embedding_{i}'] = float(embedding_array[i])
    
    return features

def extract_city_and_reviews_from_raw_json(listing_id: str, raw_data_dir: Path) -> tuple:
    """Extract city and number of reviews from raw JSON files"""
    for json_file in raw_data_dir.glob("place_id_*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            if "data" in data and "list" in data["data"]:
                for listing_obj in data["data"]["list"]:
                    listing_data = listing_obj.get("listing", {})
                    if str(listing_data.get("id", "")) == listing_id:
                        city = listing_data.get("legacyCity") or listing_data.get("legacyLocalizedCityName")
                        if not city:
                            demand = listing_obj.get("demandStayListing", {})
                            location = demand.get("location", {})
                            city = location.get("city") or location.get("localizedCityName")
                        
                        num_reviews = None
                        rating_str = listing_obj.get("avgRatingLocalized", "")
                        if rating_str and "(" in rating_str:
                            try:
                                reviews_part = rating_str.split("(")[1].split(")")[0]
                                num_reviews = int(reviews_part)
                            except:
                                pass
                        
                        return (city, num_reviews)
        except:
            continue
    return (None, None)

def extract_city_from_raw_json(listing_id: str, raw_data_dir: Path) -> str:
    """Extract city from raw JSON files"""
    for json_file in raw_data_dir.glob("place_id_*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            if "data" in data and "list" in data["data"]:
                for listing_obj in data["data"]["list"]:
                    listing_data = listing_obj.get("listing", {})
                    if str(listing_data.get("id", "")) == listing_id:
                        city = listing_data.get("legacyCity") or listing_data.get("legacyLocalizedCityName")
                        if city:
                            return city
                        
                        demand = listing_obj.get("demandStayListing", {})
                        location = demand.get("location", {})
                        city = location.get("city") or location.get("localizedCityName")
                        if city:
                            return city
        except:
            continue
    return None

def extract_text_features(name: str) -> Dict[str, float]:
    if not name:
        return {
            'name_length': 0.0,
            'name_word_count': 0.0,
            'has_mention_of_luxury': 0.0,
            'has_mention_of_beach': 0.0,
            'has_mention_of_pool': 0.0,
            'has_mention_of_parking': 0.0
        }
    
    name_lower = name.lower()
    
    return {
        'name_length': float(len(name)),
        'name_word_count': float(len(name.split())),
        'has_mention_of_luxury': 1.0 if any(word in name_lower for word in ['luxury', 'premium', 'deluxe', 'executive']) else 0.0,
        'has_mention_of_beach': 1.0 if 'beach' in name_lower else 0.0,
        'has_mention_of_pool': 1.0 if 'pool' in name_lower else 0.0,
        'has_mention_of_parking': 1.0 if 'parking' in name_lower else 0.0
    }

def calculate_location_features(lat: float, lng: float) -> Dict[str, float]:
    if lat is None or lng is None:
        return {
            'lat': 0.0,
            'lng': 0.0,
            'distance_to_center_la': 0.0,
            'distance_to_center_nyc': 0.0
        }
    
    la_center = (34.0522, -118.2437)
    nyc_center = (40.7128, -74.0060)
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    return {
        'lat': float(lat),
        'lng': float(lng),
        'distance_to_center_la': haversine_distance(lat, lng, la_center[0], la_center[1]),
        'distance_to_center_nyc': haversine_distance(lat, lng, nyc_center[0], nyc_center[1])
    }

def prepare_dataset(output_path: str = "data/training_dataset.parquet"):
    print("Connecting to database...")
    conn = get_db_connection()
    
    print("Loading data from database...")
    query = """
        SELECT 
            id,
            price,
            lat,
            lng,
            name,
            rating,
            embedding::text as embedding,
            created_at
        FROM listings
        WHERE price IS NOT NULL
        AND embedding IS NOT NULL
        AND embedding::text != '[0,0,0,0]'
        ORDER BY created_at DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Loaded {len(df)} records from database")
    
    raw_data_dir = Path("data/raw")
    if not raw_data_dir.exists():
        print(f"Warning: Raw data directory {raw_data_dir} not found. City extraction will be skipped.")
        raw_data_dir = None
    
    if len(df) == 0:
        print("No data found! Cannot create training dataset.")
        return
    
    print("Extracting features...")
    
    rows = []
    for idx, row in df.iterrows():
        if idx % 100 == 0:
            print(f"Processing row {idx+1}/{len(df)}...")
        
        city = None
        num_reviews = None
        if raw_data_dir:
            city, num_reviews = extract_city_and_reviews_from_raw_json(row['id'], raw_data_dir)
        
        features = {
            'id': row['id'],
            'price': float(row['price']),
            'rating': float(row['rating']) if pd.notna(row['rating']) else 0.0,
            'has_rating': 1.0 if pd.notna(row['rating']) else 0.0,
            'num_reviews': float(num_reviews) if num_reviews is not None else 0.0,
            'has_reviews': 1.0 if num_reviews is not None and num_reviews > 0 else 0.0,
            'city': city if city else 'Unknown'
        }
        
        embedding_features = {f'embedding_{i}': 0.0 for i in range(512)}
        if row['embedding'] is not None:
            try:
                if isinstance(row['embedding'], str):
                    import json
                    embedding_array = np.array(json.loads(row['embedding']))
                else:
                    embedding_array = np.array(row['embedding'])
                
                if embedding_array.size == 512:
                    embedding_features = extract_embedding_features(embedding_array)
            except Exception as e:
                print(f"Warning: Could not parse embedding for {row['id']}: {e}")
        
        features.update(embedding_features)
        
        text_features = extract_text_features(row['name'])
        features.update(text_features)
        
        location_features = calculate_location_features(row['lat'], row['lng'])
        features.update(location_features)
        
        rows.append(features)
    
    print("Creating DataFrame...")
    dataset_df = pd.DataFrame(rows)
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving dataset to {output_path}...")
    dataset_df.to_parquet(output_path, index=False, engine='pyarrow')
    
    print(f"\nDataset saved successfully!")
    print(f"Total records: {len(dataset_df)}")
    print(f"Total features: {len(dataset_df.columns) - 1} (excluding 'id')")
    print(f"Target variable: price")
    print(f"\nDataset statistics:")
    print(dataset_df[['price', 'rating', 'lat', 'lng']].describe())
    print(f"\nFeature columns:")
    feature_cols = [col for col in dataset_df.columns if col not in ['id', 'price']]
    metadata_features = [c for c in feature_cols if not c.startswith('embedding_')]
    embedding_features = [c for c in feature_cols if c.startswith('embedding_')]
    print(f"  - Metadata features: {len(metadata_features)}")
    print(f"  - Embedding features: {len(embedding_features)}")
    print(f"\nMetadata features: {metadata_features}")
    
    return dataset_df

if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "data/training_dataset.parquet"
    prepare_dataset(output_path)

