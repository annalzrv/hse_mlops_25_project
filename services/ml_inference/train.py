import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

from preprocessing import Preprocessor, prepare_data_for_training

def train_model(
    train_path: str = "data/train.parquet",
    test_path: str = "data/test.parquet",
    model_output_dir: str = "models",
    preprocessor_output_path: str = "models/preprocessor.pkl"
):
    """
    Train model for price prediction.
    
    Args:
        train_path: Path to training dataset
        test_path: Path to test dataset (for evaluation)
        model_output_dir: Directory to save model
        preprocessor_output_path: Path to save preprocessor
    """
    print("=" * 60)
    print("Training Real Estate Price Prediction Model")
    print("=" * 60)
    
    print(f"\nLoading data from:")
    print(f"  Train: {train_path}")
    print(f"  Test: {test_path}")
    
    X_train, y_train, X_test, y_test, preprocessor = prepare_data_for_training(
        train_path, test_path
    )
    
    print(f"\nData shape:")
    print(f"  Train: {X_train.shape}")
    print(f"  Test: {X_test.shape if X_test is not None else 'N/A'}")
    print(f"  Features: {X_train.shape[1]}")
    
    print(f"\nTarget statistics:")
    print(f"  Train - Mean: ${y_train.mean():.2f}, Std: ${y_train.std():.2f}")
    if y_test is not None:
        print(f"  Test  - Mean: ${y_test.mean():.2f}, Std: ${y_test.std():.2f}")
    
    print("\nTraining model...")
    
    try:
        from catboost import CatBoostRegressor
        
        print("Using CatBoost Regressor")
        
        model = CatBoostRegressor(
            iterations=1000,
            learning_rate=0.1,
            depth=6,
            loss_function='RMSE',
            eval_metric='RMSE',
            random_seed=42,
            verbose=100,
            early_stopping_rounds=50
        )
        
        if X_test is not None and y_test is not None:
            model.fit(
                X_train, y_train,
                eval_set=(X_test, y_test),
                use_best_model=True
            )
        else:
            model.fit(X_train, y_train)
        
        print("\nModel training completed!")
        
        train_pred = model.predict(X_train)
        train_rmse = np.sqrt(np.mean((y_train - train_pred) ** 2))
        train_mae = np.mean(np.abs(y_train - train_pred))
        train_mape = np.mean(np.abs((y_train - train_pred) / y_train)) * 100
        
        print(f"\nTrain metrics:")
        print(f"  RMSE: ${train_rmse:.2f}")
        print(f"  MAE: ${train_mae:.2f}")
        print(f"  MAPE: {train_mape:.2f}%")
        
        if X_test is not None and y_test is not None:
            test_pred = model.predict(X_test)
            test_rmse = np.sqrt(np.mean((y_test - test_pred) ** 2))
            test_mae = np.mean(np.abs(y_test - test_pred))
            test_mape = np.mean(np.abs((y_test - test_pred) / y_test)) * 100
            
            print(f"\nTest metrics:")
            print(f"  RMSE: ${test_rmse:.2f}")
            print(f"  MAE: ${test_mae:.2f}")
            print(f"  MAPE: {test_mape:.2f}%")
        
        model_path = Path(model_output_dir) / "model.cbm"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save_model(str(model_path))
        print(f"\nModel saved to: {model_path}")
        
        preprocessor.save(preprocessor_output_path)
        print(f"Preprocessor saved to: {preprocessor_output_path}")
        
        return model, preprocessor
        
    except ImportError:
        print("CatBoost not available, trying XGBoost...")
        try:
            from xgboost import XGBRegressor
            
            model = XGBRegressor(
                n_estimators=1000,
                learning_rate=0.1,
                max_depth=6,
                random_state=42,
                early_stopping_rounds=50,
                eval_metric='rmse'
            )
            
            if X_test is not None and y_test is not None:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_test, y_test)],
                    verbose=100
                )
            else:
                model.fit(X_train, y_train, verbose=100)
            
            model_path = Path(model_output_dir) / "model.json"
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model.save_model(str(model_path))
            print(f"Model saved to: {model_path}")
            
            preprocessor.save(preprocessor_output_path)
            print(f"Preprocessor saved to: {preprocessor_output_path}")
            
            return model, preprocessor
            
        except ImportError:
            print("Neither CatBoost nor XGBoost available. Please install one of them.")
            print("  pip install catboost")
            print("  or")
            print("  pip install xgboost")
            sys.exit(1)


if __name__ == "__main__":
    train_path = sys.argv[1] if len(sys.argv) > 1 else "data/train.parquet"
    test_path = sys.argv[2] if len(sys.argv) > 2 else "data/test.parquet"
    model_dir = sys.argv[3] if len(sys.argv) > 3 else "models"
    
    train_model(train_path, test_path, model_dir)

