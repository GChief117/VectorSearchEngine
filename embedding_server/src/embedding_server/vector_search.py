"""Vector search implementation for embedding database."""
import asyncio
import logging
from typing import List, Tuple, Any
import numpy as np
from pathlib import Path

from embedding_server.gibson.database import AsyncEmbeddingDatabase
from embedding_server.gibson.embedding import AsyncEmbeddingService
from embedding_server.gibson.exceptions import FlakyNetworkException
from embedding_server.redis_cache import RedisCache  # Add this import

logger = logging.getLogger(__name__)


class VectorSearchDatabase(AsyncEmbeddingDatabase):
    """Extended database with vector similarity search capabilities."""
    
    def __init__(self, cache_path: Path):
        """Initialize the vector search database.
        
        Args:
            cache_path: Path to the cache file where the database is stored.
        """
        super().__init__(cache_path)
        self.embedding_service = AsyncEmbeddingService()
    
    async def search(
        self, 
        query_text: str, 
        top_k: int = 5,
        max_retries: int = 3
    ) -> List[Tuple[str, float, str]]:
        """Search for similar embeddings using cosine similarity.
        
        Args:
            query_text: Text to search for.
            top_k: Number of results to return.
            max_retries: Maximum number of retries for network errors.
            
        Returns:
            List of tuples containing (id, similarity_score, text) sorted by similarity.
            
        Raises:
            FlakyNetworkException: If network errors persist after retries.
        """
        # Get query embedding with retry logic
        query_embedding = await self._get_embedding_with_retry(
            query_text, max_retries
        )
        
        # Calculate similarities
        results = []
        for _, row in self.data.iterrows():
            similarity = self._cosine_similarity(
                np.array(query_embedding), 
                np.array(row["Embeddings"])
            )
            results.append((row["ID"], similarity, row["Text"]))
        
        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    async def _get_embedding_with_retry(
        self, 
        text: str, 
        max_retries: int
    ) -> List[float]:
        """Get embedding with exponential backoff retry logic.
        
        Args:
            text: Text to embed.
            max_retries: Maximum number of retry attempts.
            
        Returns:
            Embedding vector.
            
        Raises:
            FlakyNetworkException: If all retries fail.
        """
        for attempt in range(max_retries):
            try:
                return await self.embedding_service.embed(text)
            except FlakyNetworkException:
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts")
                    raise
                
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(
                    f"Network error on attempt {attempt + 1}, "
                    f"retrying in {wait_time}s"
                )
                await asyncio.sleep(wait_time)
        
        raise FlakyNetworkException("Should not reach here")
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray[Any, np.dtype[np.float64]], vec2: np.ndarray[Any, np.dtype[np.float64]]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector.
            vec2: Second vector.
            
        Returns:
            Cosine similarity score between -1 and 1.
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# Add the cached version below the original class
class CachedVectorSearchDatabase(VectorSearchDatabase):
    """Vector search database with Redis caching."""
    
    def __init__(self, cache_path: Path, redis_url: str = "redis://localhost:6379"):
        """Initialize cached vector search database.
        
        Args:
            cache_path: Path to the cache file where the database is stored.
            redis_url: Redis connection URL.
        """
        super().__init__(cache_path)
        self.cache = RedisCache(redis_url)
    
    async def setup(self) -> None:
        """Initialize database and cache."""
        await super().setup()
        await self.cache.connect()
    
    async def search(
        self, 
        query_text: str, 
        top_k: int = 5,
        max_retries: int = 3,
        use_cache: bool = True
    ) -> List[Tuple[str, float, str]]:
        """Search with caching support.
        
        Args:
            query_text: Text to search for.
            top_k: Number of results to return.
            max_retries: Maximum number of retries for network errors.
            use_cache: Whether to use cache.
            
        Returns:
            List of tuples containing (id, similarity_score, text) sorted by similarity.
        """
        # Check cache first
        if use_cache:
            cached_results = await self.cache.get(query_text, top_k)
            if cached_results is not None:
                return cached_results
        
        # Perform search
        results = await super().search(query_text, top_k, max_retries)
        
        # Cache results
        if use_cache:
            await self.cache.set(query_text, top_k, results)
        
        return results
    
    async def close(self):
        """Close database and cache connections."""
        await self.cache.disconnect()