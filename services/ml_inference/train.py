import pandas as pd
import numpy as np
from pathlib import Path
import sys
from sklearn.model_selection import train_test_split

from preprocessing import prepare_data_for_training

# Try to import Optuna for hyperparameter tuning
try:
    import optuna
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print("Optuna not available. Install with: pip install optuna")


def calculate_mape(y_true, y_pred):
    """Calculate Mean Absolute Percentage Error"""
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100


def train_with_optuna(
    X_train, y_train, X_val, y_val,
    n_trials: int = 50,
    timeout: int = 1800  # 30 minutes max
):
    """
    Use Optuna to find optimal CatBoost hyperparameters.
    Optimizes for validation MAPE.
    """
    from catboost import CatBoostRegressor

    def objective(trial):
        params = {
            'iterations': trial.suggest_int('iterations', 300, 1500),
            'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
            'depth': trial.suggest_int('depth', 4, 10),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1.0, 30.0),
            'min_data_in_leaf': trial.suggest_int('min_data_in_leaf', 1, 50),
            'random_strength': trial.suggest_float('random_strength', 0.1, 10.0),
            'bagging_temperature': trial.suggest_float('bagging_temperature', 0.0, 1.0),
            'loss_function': 'RMSE',
            'eval_metric': 'RMSE',
            'random_seed': 42,
            'verbose': 0
        }

        model = CatBoostRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=(X_val, y_val),
            early_stopping_rounds=50,
            verbose=0
        )

        val_pred = model.predict(X_val)
        mape = calculate_mape(y_val, val_pred)

        return mape

    print("\n" + "=" * 60)
    print("Starting Optuna Hyperparameter Optimization")
    print("=" * 60)
    print(f"  Trials: {n_trials}")
    print(f"  Timeout: {timeout}s ({timeout/60:.1f} min)")
    print("  Objective: Minimize validation MAPE")

    # Create study with TPE sampler
    sampler = TPESampler(seed=42)
    study = optuna.create_study(
        direction='minimize',
        sampler=sampler,
        study_name='catboost_price_prediction'
    )

    # Suppress Optuna logs
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=timeout,
        show_progress_bar=True
    )

    print(f"\n  Best trial: #{study.best_trial.number}")
    print(f"  Best MAPE: {study.best_value:.2f}%")
    print("\n  Best hyperparameters:")
    for key, value in study.best_params.items():
        print(f"    {key}: {value}")

    return study.best_params


def train_model(
    train_path: str = "data/train.parquet",
    test_path: str = "data/test.parquet",
    model_output_dir: str = "models",
    preprocessor_output_path: str = "models/preprocessor.pkl",
    use_optuna: bool = True,
    optuna_trials: int = 50
):
    """
    Train model for price prediction.

    Args:
        train_path: Path to training dataset
        test_path: Path to test dataset (for evaluation)
        model_output_dir: Directory to save model
        preprocessor_output_path: Path to save preprocessor
        use_optuna: Whether to use Optuna for hyperparameter tuning
        optuna_trials: Number of Optuna trials
    """
    print("=" * 60)
    print("Training Real Estate Price Prediction Model v4.0")
    print("=" * 60)

    print("\nLoading data from:")
    print(f"  Train: {train_path}")
    print(f"  Test: {test_path}")

    X_train, y_train, X_test, y_test, preprocessor = prepare_data_for_training(
        train_path, test_path
    )

    print("\nData shape:")
    print(f"  Train: {X_train.shape}")
    print(f"  Test: {X_test.shape if X_test is not None else 'N/A'}")
    print(f"  Features: {X_train.shape[1]}")

    print("\nTarget statistics:")
    print(f"  Train - Mean: ${y_train.mean():.2f}, Std: ${y_train.std():.2f}")
    if y_test is not None:
        print(f"  Test  - Mean: ${y_test.mean():.2f}, Std: ${y_test.std():.2f}")

    print("\nSplitting train set into train/validation...")
    X_train_split, X_val_split, y_train_split, y_val_split = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42
    )
    print(f"  Train split: {X_train_split.shape[0]} samples")
    print(f"  Validation split: {X_val_split.shape[0]} samples")

    try:
        from catboost import CatBoostRegressor

        # Determine hyperparameters
        if use_optuna and OPTUNA_AVAILABLE:
            best_params = train_with_optuna(
                X_train_split, y_train_split,
                X_val_split, y_val_split,
                n_trials=optuna_trials
            )

            # Train final model with best params on full training set
            print("\n" + "=" * 60)
            print("Training Final Model with Best Hyperparameters")
            print("=" * 60)

            model = CatBoostRegressor(
                **best_params,
                loss_function='RMSE',
                eval_metric='RMSE',
                random_seed=42,
                verbose=100
            )
        else:
            print("\nUsing default CatBoost hyperparameters...")
            model = CatBoostRegressor(
                iterations=500,
                learning_rate=0.01,
                depth=5,
                l2_leaf_reg=10,
                loss_function='RMSE',
                eval_metric='RMSE',
                random_seed=42,
                verbose=100
            )

        # Train on full training set
        model.fit(
            X_train, y_train,
            eval_set=(X_val_split, y_val_split),
            use_best_model=False,
            verbose=100
        )

        print("\nModel training completed!")

        # Calculate metrics
        train_pred = model.predict(X_train)
        train_rmse = np.sqrt(np.mean((y_train - train_pred) ** 2))
        train_mae = np.mean(np.abs(y_train - train_pred))
        train_mape = calculate_mape(y_train, train_pred)

        val_pred = model.predict(X_val_split)
        val_rmse = np.sqrt(np.mean((y_val_split - val_pred) ** 2))
        val_mae = np.mean(np.abs(y_val_split - val_pred))
        val_mape = calculate_mape(y_val_split, val_pred)

        print("\nTrain metrics (full train set):")
        print(f"  RMSE: ${train_rmse:.2f}")
        print(f"  MAE: ${train_mae:.2f}")
        print(f"  MAPE: {train_mape:.2f}%")

        print("\nValidation metrics:")
        print(f"  RMSE: ${val_rmse:.2f}")
        print(f"  MAE: ${val_mae:.2f}")
        print(f"  MAPE: {val_mape:.2f}%")

        if X_test is not None and y_test is not None:
            test_pred = model.predict(X_test)
            test_rmse = np.sqrt(np.mean((y_test - test_pred) ** 2))
            test_mae = np.mean(np.abs(y_test - test_pred))
            test_mape = calculate_mape(y_test, test_pred)

            print("\nTest set metrics (holdout):")
            print(f"  RMSE: ${test_rmse:.2f}")
            print(f"  MAE: ${test_mae:.2f}")
            print(f"  MAPE: {test_mape:.2f}%")

        # Feature importance
        print("\nTop 20 Feature Importances:")
        feature_importance = model.get_feature_importance()
        feature_names = preprocessor.get_feature_names() if hasattr(preprocessor, 'get_feature_names') else [f'f_{i}' for i in range(len(feature_importance))]

        importance_df = pd.DataFrame({
            'feature': feature_names[:len(feature_importance)],
            'importance': feature_importance
        }).sort_values('importance', ascending=False)

        for i, row in importance_df.head(20).iterrows():
            print(f"  {row['feature']}: {row['importance']:.2f}")

        # Save model
        model_path = Path(model_output_dir) / "model.cbm"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save_model(str(model_path))
        print(f"\nModel saved to: {model_path}")

        preprocessor.save(preprocessor_output_path)
        print(f"Preprocessor saved to: {preprocessor_output_path}")

        return model, preprocessor

    except ImportError:
        print("CatBoost not available. Please install: pip install catboost")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train price prediction model")
    parser.add_argument("--train", type=str, default="data/train.parquet", help="Training data path")
    parser.add_argument("--test", type=str, default="data/test.parquet", help="Test data path")
    parser.add_argument("--model-dir", type=str, default="models", help="Model output directory")
    parser.add_argument("--no-optuna", action="store_true", help="Disable Optuna tuning")
    parser.add_argument("--trials", type=int, default=50, help="Number of Optuna trials")

    args = parser.parse_args()

    train_model(
        train_path=args.train,
        test_path=args.test,
        model_output_dir=args.model_dir,
        use_optuna=not args.no_optuna,
        optuna_trials=args.trials
    )
