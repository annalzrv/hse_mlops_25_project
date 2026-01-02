import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
import sys

def split_dataset(
    input_path: str = "data/training_dataset.parquet",
    train_path: str = "data/train.parquet",
    test_path: str = "data/test.parquet",
    test_size: float = 0.2,
    random_state: int = 42
):
    """
    Split dataset into train and test sets for model training and retraining.

    Args:
        input_path: Path to the full training dataset
        train_path: Path to save train dataset
        test_path: Path to save test dataset (for retraining evaluation)
        test_size: Proportion of dataset to include in test set (default 0.2 = 20%)
        random_state: Random seed for reproducibility
    """
    print(f"Loading dataset from {input_path}...")
    df = pd.read_parquet(input_path)

    print(f"Total records: {len(df)}")
    print(f"Total features: {len(df.columns) - 2} (excluding 'id' and 'price')")

    X = df.drop(columns=['id', 'price'])
    y = df['price']
    ids = df['id']

    print("\nSplitting dataset:")
    print(f"  Test size: {test_size * 100:.0f}%")
    print(f"  Random state: {random_state}")

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X, y, ids,
        test_size=test_size,
        random_state=random_state,
        shuffle=True
    )

    train_df = pd.DataFrame(X_train)
    train_df['id'] = ids_train.reset_index(drop=True)
    train_df['price'] = y_train.reset_index(drop=True)

    test_df = pd.DataFrame(X_test)
    test_df['id'] = ids_test.reset_index(drop=True)
    test_df['price'] = y_test.reset_index(drop=True)

    output_dir = Path(train_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nSaving datasets...")
    train_df.to_parquet(train_path, index=False, engine='pyarrow')
    test_df.to_parquet(test_path, index=False, engine='pyarrow')

    print("\nDataset split completed!")
    print(f"Train set: {len(train_df)} records -> {train_path}")
    print(f"Test set: {len(test_df)} records -> {test_path}")

    print("\nPrice statistics:")
    print(f"Train - Mean: ${train_df['price'].mean():.2f}, Std: ${train_df['price'].std():.2f}")
    print(f"Test  - Mean: ${test_df['price'].mean():.2f}, Std: ${test_df['price'].std():.2f}")

    return train_df, test_df

if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/training_dataset.parquet"
    train_path = sys.argv[2] if len(sys.argv) > 2 else "data/train.parquet"
    test_path = sys.argv[3] if len(sys.argv) > 3 else "data/test.parquet"

    split_dataset(input_path, train_path, test_path)

