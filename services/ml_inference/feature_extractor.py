import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Optional, Set
from math import radians, sin, cos, sqrt, atan2

# PCA configuration (must match training)
# With Mean+Max+Std aggregation, embeddings are 1536-dim (3x512)
EMBEDDING_DIM = 1536
PCA_N_COMPONENTS = 100

# Global PCA model (loaded lazily)
_pca_model = None


def get_pca_model():
    """Load PCA model lazily"""
    global _pca_model
    if _pca_model is None:
        pca_path = Path(__file__).parent / "models" / "pca.pkl"
        if pca_path.exists():
            _pca_model = joblib.load(pca_path)
        else:
            # Fallback: no PCA (for backwards compatibility with old model)
            _pca_model = None
    return _pca_model


def apply_pca_to_embedding(embedding: np.ndarray) -> np.ndarray:
    """Apply PCA transformation to embedding (1536-dim -> 100-dim)"""
    pca = get_pca_model()
    if pca is None:
        # No PCA model - return original embedding (backwards compat)
        return embedding

    if embedding is None or len(embedding) == 0:
        return np.zeros(PCA_N_COMPONENTS)

    embedding = np.array(embedding).flatten()

    # Pad to expected dimension if needed
    if len(embedding) < EMBEDDING_DIM:
        padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        padded[:len(embedding)] = embedding
        embedding = padded
    elif len(embedding) > EMBEDDING_DIM:
        embedding = embedding[:EMBEDDING_DIM]

    # Ensure correct shape for PCA
    embedding = embedding.reshape(1, -1)
    reduced = pca.transform(embedding)
    return reduced.flatten()


# Key amenities to extract as features (must match training)
KEY_AMENITIES = [
    'wifi', 'kitchen', 'washer', 'dryer', 'air conditioning', 'heating',
    'tv', 'pool', 'hot tub', 'gym', 'elevator', 'parking',
    'smoke alarm', 'carbon monoxide alarm', 'fire extinguisher',
    'dishwasher', 'refrigerator', 'microwave', 'oven', 'coffee maker',
    'self check-in', 'lockbox', 'keypad', 'smart lock',
    'beach access', 'waterfront', 'lake access',
    'patio or balcony', 'backyard', 'garden',
    'crib', 'high chair', 'pets allowed'
]


def extract_amenity_features(amenities: Optional[Set[str]] = None) -> Dict[str, float]:
    """Extract binary amenity features"""
    if amenities is None:
        amenities = set()

    amenities_lower = {a.lower() for a in amenities}

    features = {}
    for amenity in KEY_AMENITIES:
        feature_name = f"has_{amenity.replace(' ', '_').replace('-', '_')}"
        features[feature_name] = 1.0 if amenity in amenities_lower else 0.0

    return features


def extract_text_features(name: Optional[str]) -> Dict[str, float]:
    if not name:
        name = ""
    name_lower = name.lower()

    return {
        'name_length': float(len(name)),
        'name_word_count': float(len(name.split())),
        'has_mention_of_luxury': 1.0 if any(word in name_lower for word in ['luxury', 'premium', 'deluxe', 'executive']) else 0.0,
        'has_mention_of_beach': 1.0 if 'beach' in name_lower else 0.0,
        'has_mention_of_pool': 1.0 if 'pool' in name_lower else 0.0,
        'has_mention_of_parking': 1.0 if 'parking' in name_lower else 0.0
    }


def calculate_location_features(lat: Optional[float], lng: Optional[float]) -> Dict[str, float]:
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


def extract_embedding_features(embedding: np.ndarray) -> Dict[str, float]:
    if embedding is None or (hasattr(embedding, 'size') and embedding.size == 0):
        return {f'embedding_{i}': 0.0 for i in range(512)}

    if hasattr(embedding, 'ndim') and embedding.ndim > 1:
        embedding = embedding.flatten()

    embedding = np.array(embedding)

    if len(embedding) != 512:
        padded = np.zeros(512, dtype=np.float32)
        padded[:min(len(embedding), 512)] = embedding[:min(len(embedding), 512)]
        embedding = padded

    return {f'embedding_{i}': float(embedding[i]) for i in range(512)}


def extract_property_type_features(property_type: Optional[str], room_type: Optional[str]) -> Dict[str, float]:
    """Extract property type and room type binary features"""
    property_type_lower = str(property_type or '').lower()
    room_type_lower = str(room_type or '').lower()

    return {
        'is_entire_place': 1.0 if 'entire' in property_type_lower else 0.0,
        'is_private_room': 1.0 if 'private room' in property_type_lower else 0.0,
        'is_shared_room': 1.0 if 'shared' in property_type_lower else 0.0,
        'is_hotel': 1.0 if 'hotel' in property_type_lower else 0.0,
        'room_type_entire': 1.0 if 'entire' in room_type_lower else 0.0,
        'room_type_private': 1.0 if 'private' in room_type_lower else 0.0,
        'room_type_shared': 1.0 if 'shared' in room_type_lower else 0.0
    }


def prepare_features_from_listing(
    listing_data: Dict,
    embedding: Optional[np.ndarray] = None,
    city: Optional[str] = None,
    num_reviews: Optional[int] = None,
    amenities: Optional[Set[str]] = None
) -> pd.DataFrame:
    """
    Prepare features for prediction.

    Supports both old model (without detailed features) and new model (with detailed features).
    """
    features = {}

    # Use review_count from listing_data if available
    if num_reviews is None:
        num_reviews = listing_data.get('review_count')

    # Rating handling
    rating = listing_data.get('rating')
    # If no overall rating, try to compute from detailed ratings
    if rating is None:
        detailed_ratings = [
            listing_data.get('cleanliness_rating'),
            listing_data.get('location_rating'),
            listing_data.get('value_rating'),
            listing_data.get('communication_rating'),
            listing_data.get('checkin_rating'),
            listing_data.get('accuracy_rating')
        ]
        valid_ratings = [r for r in detailed_ratings if r is not None]
        if valid_ratings:
            rating = sum(valid_ratings) / len(valid_ratings)

    features['rating'] = float(rating) if rating is not None else 0.0
    features['has_rating'] = 1.0 if rating is not None and rating > 0 else 0.0
    features['num_reviews'] = float(num_reviews) if num_reviews is not None else 0.0
    features['has_reviews'] = 1.0 if num_reviews is not None and num_reviews > 0 else 0.0
    features['city'] = city if city else 'Unknown'

    # New detailed features
    features['person_capacity'] = float(listing_data.get('person_capacity') or 0)
    features['bedrooms'] = float(listing_data.get('bedrooms') or 0)
    features['beds'] = float(listing_data.get('beds') or 0)
    features['bathrooms'] = float(listing_data.get('bathrooms') or 0)

    # Detailed ratings
    features['cleanliness_rating'] = float(listing_data.get('cleanliness_rating') or 0)
    features['location_rating'] = float(listing_data.get('location_rating') or 0)
    features['value_rating'] = float(listing_data.get('value_rating') or 0)
    features['communication_rating'] = float(listing_data.get('communication_rating') or 0)
    features['checkin_rating'] = float(listing_data.get('checkin_rating') or 0)
    features['accuracy_rating'] = float(listing_data.get('accuracy_rating') or 0)

    # Property type features
    property_features = extract_property_type_features(
        listing_data.get('property_type'),
        listing_data.get('room_type')
    )
    features.update(property_features)

    # Amenity features
    amenity_features = extract_amenity_features(amenities)
    features.update(amenity_features)

    # Embeddings with PCA reduction
    pca = get_pca_model()
    if pca is not None:
        # Use PCA-reduced embeddings (v4.0 model with Mean+Max+Std)
        if embedding is not None and len(embedding) > 0:
            embedding_arr = np.array(embedding).flatten()
            # Support both 512-dim (legacy) and 1536-dim (new Mean+Max+Std) embeddings
            if len(embedding_arr) in (512, EMBEDDING_DIM):
                pca_features = apply_pca_to_embedding(embedding_arr)
                for i in range(PCA_N_COMPONENTS):
                    features[f'pca_{i}'] = float(pca_features[i])
            else:
                for i in range(PCA_N_COMPONENTS):
                    features[f'pca_{i}'] = 0.0
        else:
            for i in range(PCA_N_COMPONENTS):
                features[f'pca_{i}'] = 0.0
    else:
        # Fallback to raw embeddings (v2.0 model backwards compat)
        embedding_features = extract_embedding_features(embedding)
        for i in range(512):
            features[f'embedding_{i}'] = embedding_features[f'embedding_{i}']

    # Text features from name
    text_features = extract_text_features(listing_data.get('name'))
    features['name_length'] = text_features['name_length']
    features['name_word_count'] = text_features['name_word_count']
    features['has_mention_of_luxury'] = text_features['has_mention_of_luxury']
    features['has_mention_of_beach'] = text_features['has_mention_of_beach']
    features['has_mention_of_pool'] = text_features['has_mention_of_pool']
    features['has_mention_of_parking'] = text_features['has_mention_of_parking']

    # Location features
    location_features = calculate_location_features(
        listing_data.get('lat'),
        listing_data.get('lng')
    )
    features['lat'] = location_features['lat']
    features['lng'] = location_features['lng']
    features['distance_to_center_la'] = location_features['distance_to_center_la']
    features['distance_to_center_nyc'] = location_features['distance_to_center_nyc']

    return pd.DataFrame([features])
