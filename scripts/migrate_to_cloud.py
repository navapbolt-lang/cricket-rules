"""Migrate data from local Qdrant to Qdrant Cloud."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance


LOCAL_URL = "http://localhost:6333"
COLLECTION_NAME = "icc_laws"
BATCH_SIZE = 100


def migrate():
    # Connect to local Qdrant
    local_client = QdrantClient(url=LOCAL_URL)
    print(f"Connected to local Qdrant at {LOCAL_URL}")

    # Get Qdrant Cloud credentials from env
    cloud_url = os.getenv("QDRANT_URL")
    cloud_api_key = os.getenv("QDRANT_API_KEY")

    if not cloud_url or not cloud_api_key:
        print("ERROR: Set QDRANT_URL and QDRANT_API_KEY environment variables")
        print("Example:")
        print("  set QDRANT_URL=https://xxxxx.qdrant.io:6333")
        print("  set QDRANT_API_KEY=your_api_key_here")
        return

    # Connect to Qdrant Cloud
    cloud_client = QdrantClient(url=cloud_url, api_key=cloud_api_key)
    print(f"Connected to Qdrant Cloud at {cloud_url}")

    # Get local collection info
    local_info = local_client.get_collection(COLLECTION_NAME)
    total_points = local_info.points_count
    print(f"Local collection has {total_points} points")

    # Create collection in cloud if it doesn't exist
    try:
        cloud_client.get_collection(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' already exists in cloud")
    except Exception:
        print(f"Creating collection '{COLLECTION_NAME}' in cloud...")
        cloud_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=local_info.config.params.vectors.size,
                distance=Distance.COSINE,
            ),
        )
        print("Collection created")

    # Migrate in batches
    migrated = 0
    offset = None

    while True:
        # Scroll through local points
        points, offset = local_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )

        if not points:
            break

        # Upload to cloud
        cloud_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )

        migrated += len(points)
        print(f"Migrated {migrated}/{total_points} points...")

        if offset is None:
            break

    print(f"\nDone! Migrated {migrated} points to Qdrant Cloud")
    print(f"Update your Render env var: QDRANT_URL={cloud_url}")


if __name__ == "__main__":
    migrate()
