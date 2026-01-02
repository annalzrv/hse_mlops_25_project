import os
import psycopg2
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict
import json
import joblib
from sklearn.decomposition import PCA

load_dotenv()

# PCA configuration
# With Mean+Max+Std aggregation, embeddings are 1536-dim (3x512)
# We reduce to 100 components to capture more variance while keeping metadata important
EMBEDDING_DIM = 1536  # Mean (512) + Max (512) + Std (512)
PCA_N_COMPONENTS = 100

def get_db_connection(host: str = None, port: str = None):
    conn = psycopg2.connect(
        host=host or os.getenv("POSTGRES_HOST", "localhost"),
        port=port or os.getenv("POSTGRES_PORT", "5433"),
        database=os.getenv("POSTGRES_DB", "real_estate"),
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops123")
    )
    return conn

def extract_embedding_features(embedding_array: np.ndarray, expected_dim: int = EMBEDDING_DIM) -> Dict[str, float]:
    """Extract embedding features from array. Supports both 512-dim and 1536-dim embeddings."""
    if embedding_array is None or len(embedding_array) == 0:
        return {}

    features = {}
    for i in range(min(expected_dim, len(embedding_array))):
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

def get_amenities_for_listing(conn, listing_id: str) -> Dict[str, float]:
    """Get amenity binary features for a listing"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT amenity_name FROM listing_amenities WHERE listing_id = %s",
        (listing_id,)
    )
    amenities = {row[0].lower() for row in cursor.fetchall()}
    cursor.close()

    # Define key amenities to extract as features
    key_amenities = [
        'wifi', 'kitchen', 'washer', 'dryer', 'air conditioning', 'heating',
        'tv', 'pool', 'hot tub', 'gym', 'elevator', 'parking',
        'smoke alarm', 'carbon monoxide alarm', 'fire extinguisher',
        'dishwasher', 'refrigerator', 'microwave', 'oven', 'coffee maker',
        'self check-in', 'lockbox', 'keypad', 'smart lock',
        'beach access', 'waterfront', 'lake access',
        'patio or balcony', 'backyard', 'garden',
        'crib', 'high chair', 'pets allowed'
    ]

    features = {}
    for amenity in key_amenities:
        feature_name = f"has_{amenity.replace(' ', '_').replace('-', '_')}"
        features[feature_name] = 1.0 if amenity in amenities else 0.0

    return features


def prepare_dataset(output_path: str = "data/training_dataset.parquet", db_host: str = None, db_port: str = None):
    print("Connecting to database...")
    conn = get_db_connection(host=db_host, port=db_port)

    print("Loading data from database...")
    # Updated query to include new detailed fields
    query = """
        SELECT
            id,
            price,
            lat,
            lng,
            name,
            rating,
            embedding::text as embedding,
            created_at,
            city,  -- City from detail parser
            -- New detailed fields
            property_type,
            room_type,
            person_capacity,
            bedrooms,
            beds,
            bathrooms,
            cleanliness_rating,
            location_rating,
            value_rating,
            communication_rating,
            checkin_rating,
            accuracy_rating,
            review_count,
            details_fetched_at
        FROM listings
        WHERE price IS NOT NULL
        AND embedding IS NOT NULL
        AND embedding::text != '[0,0,0,0]'
        ORDER BY created_at DESC
    """

    df = pd.read_sql_query(query, conn)

    print(f"Loaded {len(df)} records from database")
    enriched_count = df['details_fetched_at'].notna().sum()
    print(f"  - {enriched_count} listings have enriched details")

    raw_data_dir = Path("data/raw/search")
    if not raw_data_dir.exists():
        print(f"Warning: Raw data directory {raw_data_dir} not found. City extraction will be skipped.")
        raw_data_dir = None

    if len(df) == 0:
        print("No data found! Cannot create training dataset.")
        conn.close()
        return

    print("Extracting features...")

    rows = []
    for idx, row in df.iterrows():
        if idx % 100 == 0:
            print(f"Processing row {idx+1}/{len(df)}...")

        # Get city from database first (parsed from detail API)
        city = row.get('city')
        num_reviews = None

        # Fallback to raw JSON if database city is missing
        if not city and raw_data_dir:
            city, num_reviews = extract_city_and_reviews_from_raw_json(row['id'], raw_data_dir)

        # Use review_count from detailed data if available
        if pd.notna(row.get('review_count')):
            num_reviews = int(row['review_count'])

        # Use overall rating from detailed data if available (guestSatisfactionOverall)
        rating_val = row['rating']
        if pd.isna(rating_val) and pd.notna(row.get('cleanliness_rating')):
            # Compute average from detailed ratings if overall rating is missing
            detailed_ratings = [
                row.get('cleanliness_rating'),
                row.get('location_rating'),
                row.get('value_rating'),
                row.get('communication_rating'),
                row.get('checkin_rating'),
                row.get('accuracy_rating')
            ]
            valid_ratings = [r for r in detailed_ratings if pd.notna(r)]
            if valid_ratings:
                rating_val = np.mean(valid_ratings)

        features = {
            'id': row['id'],
            'price': float(row['price']),
            'rating': float(rating_val) if pd.notna(rating_val) else 0.0,
            'has_rating': 1.0 if pd.notna(rating_val) and rating_val > 0 else 0.0,
            'num_reviews': float(num_reviews) if num_reviews is not None else 0.0,
            'has_reviews': 1.0 if num_reviews is not None and num_reviews > 0 else 0.0,
            'city': city if city else 'Unknown'
        }

        # Add new detailed features
        features['person_capacity'] = float(row['person_capacity']) if pd.notna(row.get('person_capacity')) else 0.0
        features['bedrooms'] = float(row['bedrooms']) if pd.notna(row.get('bedrooms')) else 0.0
        features['beds'] = float(row['beds']) if pd.notna(row.get('beds')) else 0.0
        features['bathrooms'] = float(row['bathrooms']) if pd.notna(row.get('bathrooms')) else 0.0

        # Detailed ratings
        features['cleanliness_rating'] = float(row['cleanliness_rating']) if pd.notna(row.get('cleanliness_rating')) else 0.0
        features['location_rating'] = float(row['location_rating']) if pd.notna(row.get('location_rating')) else 0.0
        features['value_rating'] = float(row['value_rating']) if pd.notna(row.get('value_rating')) else 0.0
        features['communication_rating'] = float(row['communication_rating']) if pd.notna(row.get('communication_rating')) else 0.0
        features['checkin_rating'] = float(row['checkin_rating']) if pd.notna(row.get('checkin_rating')) else 0.0
        features['accuracy_rating'] = float(row['accuracy_rating']) if pd.notna(row.get('accuracy_rating')) else 0.0

        # Property type encoding (binary features)
        property_type = str(row.get('property_type', '')).lower()
        features['is_entire_place'] = 1.0 if 'entire' in property_type else 0.0
        features['is_private_room'] = 1.0 if 'private room' in property_type else 0.0
        features['is_shared_room'] = 1.0 if 'shared' in property_type else 0.0
        features['is_hotel'] = 1.0 if 'hotel' in property_type else 0.0

        # Room type
        room_type = str(row.get('room_type', '')).lower()
        features['room_type_entire'] = 1.0 if 'entire' in room_type else 0.0
        features['room_type_private'] = 1.0 if 'private' in room_type else 0.0
        features['room_type_shared'] = 1.0 if 'shared' in room_type else 0.0

        # Add amenity features
        amenity_features = get_amenities_for_listing(conn, row['id'])
        features.update(amenity_features)

        # Initialize embedding features with zeros for expected dimension
        embedding_features = {f'embedding_{i}': 0.0 for i in range(EMBEDDING_DIM)}
        if row['embedding'] is not None:
            try:
                if isinstance(row['embedding'], str):
                    import json
                    embedding_array = np.array(json.loads(row['embedding']))
                else:
                    embedding_array = np.array(row['embedding'])

                # Support both old 512-dim and new 1536-dim embeddings
                if embedding_array.size == EMBEDDING_DIM:
                    embedding_features = extract_embedding_features(embedding_array, EMBEDDING_DIM)
                elif embedding_array.size == 512:
                    # Legacy 512-dim embedding - pad with zeros for max/std
                    print(f"Warning: Listing {row['id']} has 512-dim embedding, expected {EMBEDDING_DIM}")
                    embedding_features = extract_embedding_features(embedding_array, 512)
            except Exception as e:
                print(f"Warning: Could not parse embedding for {row['id']}: {e}")

        features.update(embedding_features)

        text_features = extract_text_features(row['name'])
        features.update(text_features)

        location_features = calculate_location_features(row['lat'], row['lng'])
        features.update(location_features)

        rows.append(features)

    conn.close()

    print("Creating DataFrame...")
    dataset_df = pd.DataFrame(rows)

    # Apply PCA to embeddings
    print(f"\nApplying PCA to reduce embeddings from {EMBEDDING_DIM} to {PCA_N_COMPONENTS} dimensions...")
    embedding_cols = [f'embedding_{i}' for i in range(EMBEDDING_DIM)]

    # Check which embedding columns actually exist
    existing_emb_cols = [c for c in embedding_cols if c in dataset_df.columns]
    print(f"  Found {len(existing_emb_cols)} embedding columns")

    if len(existing_emb_cols) < EMBEDDING_DIM:
        print(f"  Warning: Expected {EMBEDDING_DIM} embedding columns, found {len(existing_emb_cols)}")
        # Pad missing columns with zeros
        for col in embedding_cols:
            if col not in dataset_df.columns:
                dataset_df[col] = 0.0

    embeddings_matrix = dataset_df[embedding_cols].values

    pca = PCA(n_components=PCA_N_COMPONENTS, random_state=42)
    embeddings_reduced = pca.fit_transform(embeddings_matrix)

    print(f"  Explained variance ratio: {pca.explained_variance_ratio_.sum():.2%}")

    # Save PCA model for inference
    pca_path = Path("services/ml_inference/models/pca.pkl")
    pca_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pca, pca_path)
    print(f"  PCA model saved to: {pca_path}")

    # Replace embedding columns with PCA components
    dataset_df = dataset_df.drop(columns=embedding_cols)
    for i in range(PCA_N_COMPONENTS):
        dataset_df[f'pca_{i}'] = embeddings_reduced[:, i]

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving dataset to {output_path}...")
    dataset_df.to_parquet(output_path, index=False, engine='pyarrow')

    print("\nDataset saved successfully!")
    print(f"Total records: {len(dataset_df)}")
    print(f"Total features: {len(dataset_df.columns) - 1} (excluding 'id')")
    print("Target variable: price")
    print("\nDataset statistics:")
    print(dataset_df[['price', 'rating', 'lat', 'lng']].describe())
    print("\nFeature columns:")
    feature_cols = [col for col in dataset_df.columns if col not in ['id', 'price']]
    metadata_features = [c for c in feature_cols if not c.startswith('pca_')]
    pca_features = [c for c in feature_cols if c.startswith('pca_')]
    print(f"  - Metadata features: {len(metadata_features)}")
    print(f"  - PCA embedding features: {len(pca_features)}")
    print(f"\nMetadata features: {metadata_features}")

    return dataset_df

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare training dataset from database")
    parser.add_argument(
        "--output",
        type=str,
        default="data/training_dataset.parquet",
        help="Output path for dataset"
    )
    parser.add_argument(
        "--db-host",
        type=str,
        default="localhost",
        help="Database host (default: localhost)"
    )
    parser.add_argument(
        "--db-port",
        type=str,
        default="5433",
        help="Database port (default: 5433)"
    )

    args = parser.parse_args()
    prepare_dataset(args.output, db_host=args.db_host, db_port=args.db_port)

