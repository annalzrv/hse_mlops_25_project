import pandas as pd
import numpy as np
from typing import Dict, Optional
from math import radians, sin, cos, sqrt, atan2


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


def prepare_features_from_listing(
    listing_data: Dict,
    embedding: Optional[np.ndarray] = None,
    city: Optional[str] = None,
    num_reviews: Optional[int] = None
) -> pd.DataFrame:
    """
    Prepare features in the exact order expected by the preprocessor.
    Order: rating, has_rating, num_reviews, has_reviews, city,
           embedding_0..511, name_length, name_word_count, has_mention_*,
           lat, lng, distance_to_center_la, distance_to_center_nyc
    """
    features = {}
    
    rating = listing_data.get('rating')
    features['rating'] = float(rating) if rating is not None else 0.0
    features['has_rating'] = 1.0 if rating is not None and rating > 0 else 0.0
    features['num_reviews'] = float(num_reviews) if num_reviews is not None else 0.0
    features['has_reviews'] = 1.0 if num_reviews is not None and num_reviews > 0 else 0.0
    features['city'] = city if city else 'Unknown'
    
    embedding_features = extract_embedding_features(embedding)
    for i in range(512):
        features[f'embedding_{i}'] = embedding_features[f'embedding_{i}']
    
    text_features = extract_text_features(listing_data.get('name'))
    features['name_length'] = text_features['name_length']
    features['name_word_count'] = text_features['name_word_count']
    features['has_mention_of_luxury'] = text_features['has_mention_of_luxury']
    features['has_mention_of_beach'] = text_features['has_mention_of_beach']
    features['has_mention_of_pool'] = text_features['has_mention_of_pool']
    features['has_mention_of_parking'] = text_features['has_mention_of_parking']
    
    location_features = calculate_location_features(
        listing_data.get('lat'),
        listing_data.get('lng')
    )
    features['lat'] = location_features['lat']
    features['lng'] = location_features['lng']
    features['distance_to_center_la'] = location_features['distance_to_center_la']
    features['distance_to_center_nyc'] = location_features['distance_to_center_nyc']
    
    return pd.DataFrame([features])
