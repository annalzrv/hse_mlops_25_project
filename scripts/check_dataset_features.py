import pandas as pd

df = pd.read_parquet('data/training_dataset.parquet')

metadata_cols = [c for c in df.columns if c not in ['id', 'price'] and not c.startswith('embedding_')]

print('=== Metadata features (15) ===')
for col in sorted(metadata_cols):
    print(f'  - {col}')

print(f'\nTotal features: {len(df.columns) - 1} (excluding id)')
print(f'  - Metadata: {len(metadata_cols)}')
print(f'  - Embeddings: {len([c for c in df.columns if c.startswith("embedding_")])}')

print(f'\n=== Dataset shape ===')
print(f'Rows: {len(df)}, Columns: {len(df.columns)}')

