import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from typing import Tuple, Dict
import pickle
from pathlib import Path


class Preprocessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.city_encoder = LabelEncoder()
        self.is_fitted = False
        self.feature_names = None
        
    def fit(self, df: pd.DataFrame) -> 'Preprocessor':
        """
        Fit preprocessor on training data.
        
        Args:
            df: Training dataframe with features and target
            
        Returns:
            self
        """
        X = self._prepare_features(df, fit=True)
        self.feature_names = list(X.columns)
        self.is_fitted = True
        return self
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data using fitted preprocessor.
        
        Args:
            df: Dataframe to transform
            
        Returns:
            Transformed dataframe
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor must be fitted before transform")
        
        X = self._prepare_features(df, fit=False)
        return X
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(df).transform(df)
    
    def _prepare_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Prepare features for model."""
        X = df.copy()
        
        if 'price' in X.columns:
            X = X.drop(columns=['price'])
        if 'id' in X.columns:
            X = X.drop(columns=['id'])
        
        categorical_cols = ['city']
        numerical_cols = [col for col in X.columns if col not in categorical_cols]
        
        if 'city' in X.columns:
            X['city'] = X['city'].astype(str)
            if fit:
                self.city_encoder.fit(X['city'])
                X['city'] = self.city_encoder.transform(X['city'])
            else:
                X['city'] = X['city'].map(lambda x: x if x in self.city_encoder.classes_ else 'Unknown')
                X['city'] = self.city_encoder.transform(X['city'])
        
        if fit:
            X[numerical_cols] = self.scaler.fit_transform(X[numerical_cols])
        else:
            X[numerical_cols] = self.scaler.transform(X[numerical_cols])
        
        return X
    
    def save(self, path: str):
        """Save preprocessor to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'city_encoder': self.city_encoder,
                'feature_names': self.feature_names,
                'is_fitted': self.is_fitted
            }, f)
    
    @classmethod
    def load(cls, path: str) -> 'Preprocessor':
        """Load preprocessor from disk."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        preprocessor = cls()
        preprocessor.scaler = data['scaler']
        preprocessor.city_encoder = data['city_encoder']
        preprocessor.feature_names = data['feature_names']
        preprocessor.is_fitted = data['is_fitted']
        
        return preprocessor


def prepare_data_for_training(
    train_path: str,
    test_path: str = None
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Load and prepare data for training.
    
    Args:
        train_path: Path to training dataset
        test_path: Optional path to test dataset
        
    Returns:
        X_train, y_train, X_test, y_test
    """
    print("Loading training data...")
    train_df = pd.read_parquet(train_path)
    
    print(f"Filtering out rows with missing price...")
    initial_count = len(train_df)
    train_df = train_df.dropna(subset=['price'])
    print(f"  Removed {initial_count - len(train_df)} rows with missing price")
    
    y_train = train_df['price'].values.copy()
    
    print("Preparing preprocessor...")
    preprocessor = Preprocessor()
    X_train = preprocessor.fit_transform(train_df)
    
    X_test = None
    y_test = None
    
    if test_path:
        print("Loading test data...")
        test_df = pd.read_parquet(test_path)
        initial_test_count = len(test_df)
        test_df = test_df.dropna(subset=['price'])
        print(f"  Removed {initial_test_count - len(test_df)} rows with missing price from test set")
        y_test = test_df['price'].values.copy()
        X_test = preprocessor.transform(test_df)
    
    return X_train, y_train, X_test, y_test, preprocessor

