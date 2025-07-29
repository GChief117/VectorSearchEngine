"""Redis cache implementation for vector search results."""
import json
import hashlib
from typing import List, Tuple, Optional
import redis.asyncio as redis
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache for vector search results."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL.
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.ttl = 3600  # 1 hour cache TTL
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _generate_cache_key(self, query: str, top_k: int) -> str:
        """Generate cache key from query and parameters.
        
        Args:
            query: Search query text.
            top_k: Number of results.
            
        Returns:
            Cache key string.
        """
        content = f"{query}:{top_k}"
        return f"vector_search:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def get(
        self, 
        query: str, 
        top_k: int
    ) -> Optional[List[Tuple[str, float, str]]]:
        """Get cached search results.
        
        Args:
            query: Search query text.
            top_k: Number of results.
            
        Returns:
            Cached results if available, None otherwise.
        """
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_cache_key(query, top_k)
            cached = await self.redis_client.get(key)
            
            if cached:
                logger.info(f"Cache hit for query: {query[:20]}...")
                return json.loads(cached)
            
            logger.info(f"Cache miss for query: {query[:20]}...")
            return None
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(
        self, 
        query: str, 
        top_k: int, 
        results: List[Tuple[str, float, str]]
    ):
        """Cache search results.
        
        Args:
            query: Search query text.
            top_k: Number of results.
            results: Search results to cache.
        """
        if not self.redis_client:
            return
        
        try:
            key = self._generate_cache_key(query, top_k)
            await self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(results)
            )
            logger.info(f"Cached results for query: {query[:20]}...")
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    async def clear(self):
        """Clear all cached results."""
        if not self.redis_client:
            return
        
        try:
            pattern = "vector_search:*"
            cursor = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, 
                    match=pattern, 
                    count=100
                )
                
                if keys:
                    await self.redis_client.delete(*keys)
                
                if cursor == 0:
                    break
                    
            logger.info("Cleared all cached search results")
            
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    async def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats.
        """
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info()
            pattern = "vector_search:*"
            cursor, keys = await self.redis_client.scan(
                cursor=0, 
                match=pattern, 
                count=1000
            )
            
            return {
                "status": "connected",
                "cached_queries": len(keys),
                "memory_used": info.get("used_memory_human", "unknown"),
                "hit_rate": info.get("keyspace_hits", 0) / 
                           max(info.get("keyspace_hits", 0) + 
                               info.get("keyspace_misses", 0), 1)
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"status": "error", "error": str(e)}