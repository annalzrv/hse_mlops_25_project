import numpy as np
from typing import List
from logger import setup_logger

logger = setup_logger(__name__)

class EmbeddingAggregator:
    @staticmethod
    def mean_pool_embeddings(embeddings: List[np.ndarray]) -> np.ndarray:
        if not embeddings:
            logger.warning("No embeddings provided, returning zero vector")
            return np.zeros(512, dtype=np.float32)

        if len(embeddings) == 1:
            return embeddings[0]

        stacked = np.stack(embeddings)
        mean_embedding = np.mean(stacked, axis=0)

        logger.debug(f"Aggregated {len(embeddings)} embeddings into single vector")
        return mean_embedding.astype(np.float32)

