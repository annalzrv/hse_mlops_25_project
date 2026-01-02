#!/usr/bin/env python3
"""
Regenerate embeddings for all listings using Mean+Max+Std aggregation.
Processes all images in data/images/{listing_id}/ and updates database.
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "data_loader"))

load_dotenv()


def get_db_connection():
    """Connect to PostgreSQL database (always use localhost:5433 for local script execution)."""
    return psycopg2.connect(
        host="localhost",
        port="5433",  # Docker-mapped port
        database=os.getenv("POSTGRES_DB", "real_estate"),
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops123")
    )


def get_listing_ids_from_images(images_dir: Path) -> list:
    """Get all listing IDs that have image folders."""
    listing_ids = []
    for item in images_dir.iterdir():
        if item.is_dir():
            listing_ids.append(item.name)
    return listing_ids


def get_image_paths(listing_id: str, images_dir: Path) -> list:
    """Get all image paths for a listing, sorted by filename."""
    listing_dir = images_dir / listing_id
    if not listing_dir.exists():
        return []

    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = []
    for f in listing_dir.iterdir():
        if f.suffix.lower() in image_extensions:
            images.append(str(f))

    # Sort to ensure consistent ordering (img_00, img_01, etc.)
    return sorted(images)


def update_embedding_in_db(conn, listing_id: str, embedding: np.ndarray):
    """Update the embedding for a listing in the database."""
    cursor = conn.cursor()

    # Convert numpy array to list for PostgreSQL
    embedding_list = embedding.tolist()

    cursor.execute(
        """
        UPDATE listings
        SET embedding = %s::vector
        WHERE id = %s
        """,
        (embedding_list, listing_id)
    )

    conn.commit()
    cursor.close()


def main():
    print("=" * 60)
    print("Regenerating Embeddings with Mean+Max+Std Aggregation")
    print("=" * 60)

    # Setup paths
    project_root = Path(__file__).parent.parent
    images_dir = project_root / "data" / "images"

    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        sys.exit(1)

    # Get listing IDs
    listing_ids = get_listing_ids_from_images(images_dir)
    print(f"\nFound {len(listing_ids)} listings with images")

    if not listing_ids:
        print("No listings to process!")
        return

    # Import ImageProcessor (loads CLIP model)
    print("\nLoading CLIP model...")
    from image_processor import ImageProcessor
    processor = ImageProcessor()

    # Connect to database
    print("\nConnecting to database...")
    conn = get_db_connection()

    # Check if pgvector supports 1536 dimensions
    cursor = conn.cursor()
    cursor.execute("SELECT id, embedding::text FROM listings LIMIT 1")
    sample = cursor.fetchone()
    cursor.close()

    if sample:
        print(f"Sample listing found: {sample[0]}")

    # Process each listing
    print(f"\nProcessing {len(listing_ids)} listings...")
    print("-" * 60)

    processed = 0
    errors = 0

    for i, listing_id in enumerate(listing_ids):
        try:
            # Get image paths
            image_paths = get_image_paths(listing_id, images_dir)

            if not image_paths:
                print(f"[{i+1}/{len(listing_ids)}] {listing_id}: No images found, skipping")
                continue

            # Process images with new aggregation
            embedding = processor.process_listing_images(image_paths, aggregation="mean_max_std")

            # Verify embedding dimension
            if len(embedding) != 1536:
                print(f"[{i+1}/{len(listing_ids)}] {listing_id}: Unexpected embedding dim {len(embedding)}, skipping")
                errors += 1
                continue

            # Update database
            update_embedding_in_db(conn, listing_id, embedding)

            processed += 1
            if (i + 1) % 50 == 0 or i == 0:
                print(f"[{i+1}/{len(listing_ids)}] {listing_id}: {len(image_paths)} images -> 1536d embedding ✓")

        except Exception as e:
            print(f"[{i+1}/{len(listing_ids)}] {listing_id}: Error - {e}")
            errors += 1
            conn.rollback()
            continue

    conn.close()

    print("-" * 60)
    print("\nCompleted!")
    print(f"  Processed: {processed} listings")
    print(f"  Errors: {errors}")
    print("  Embedding dimension: 1536 (Mean + Max + Std)")


if __name__ == "__main__":
    main()

