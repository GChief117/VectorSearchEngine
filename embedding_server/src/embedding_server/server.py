"""Main entry point for FastAPI application with Redis caching."""
import logging
import os
from http import HTTPStatus
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .vector_search import VectorSearchDatabase, CachedVectorSearchDatabase
from .redis_cache import RedisCache
from .gibson.embedding import AsyncEmbeddingService
from .gibson.exceptions import FlakyNetworkException

logging.basicConfig(level=logging.DEBUG if "DEBUG" in os.environ else logging.INFO)
logger = logging.getLogger(__name__)

# Create app WITHOUT docs_url first
app = FastAPI(
    title="Vector Search API",
    description="Enterprise-grade semantic search with Redis caching",
    version="1.0.0"
)

# Add CORS middleware IMMEDIATELY after app creation
origins = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "*"  # Allow all origins for development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# NOW add the docs after CORS
app.docs_url = "/docs"
app.redoc_url = "/redoc"

# Initialize database with Redis caching if available
db_path = Path(__file__).parent.parent / "data" / "embeddings.json"
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

try:
    db = CachedVectorSearchDatabase(db_path, redis_url)
    logger.info("Using Redis-cached vector search database")
except Exception as e:
    logger.warning(f"Redis unavailable, falling back to standard database: {e}")
    db = VectorSearchDatabase(db_path)

es = AsyncEmbeddingService()


class InsertRequest(BaseModel):
    """Represents an insert request."""
    text: str
    test_db: str | None = None


class SearchRequest(BaseModel):
    """Represents a search request."""
    query: str
    top_k: Optional[int] = 5
    use_cache: Optional[bool] = True


class SearchResult(BaseModel):
    """Represents a single search result."""
    id: str
    score: float
    text: str


class SearchResponse(BaseModel):
    """Represents the search response."""
    results: List[SearchResult]
    cache_hit: Optional[bool] = None


class CacheStats(BaseModel):
    """Cache statistics response."""
    status: str
    cached_queries: Optional[int] = None
    memory_used: Optional[str] = None
    hit_rate: Optional[float] = None


# Add a simple OPTIONS handler for all routes
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"message": "OK"}


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize the services asynchronously on startup."""
    await db.setup()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Vector Search API", "version": "1.0.0"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Returns a simple health check endpoint to indicate the application is ready."""
    return {"message": "Ready", "cache_enabled": hasattr(db, 'cache')}


@app.post("/insert")
async def insert_data(request: InsertRequest) -> dict[str, str]:
    """Inserts the provided text and its embeddings into the database.

    Args:
        request: The insert request containing text to embed and store.

    Returns:
        A dictionary with a message indicating successful insertion.

    Raises:
        HTTPException: An error occurred during the embedding or insertion process.
    """
    logger.debug(
        "Received insert request",
        extra={"text": request.text, "test_db": request.test_db},
    )

    # If a test database is provided, use it instead of the default database.
    if request.test_db is not None:
        test_db_path = Path(__file__).parent / request.test_db
        Path.unlink(test_db_path, missing_ok=True)
        test_db = VectorSearchDatabase(test_db_path)
        await test_db.setup()
        logger.info("Test database setup complete")
        db_to_use = test_db
    else:
        db_to_use = db

    try:
        # Handle FlakyNetworkException with retries
        max_retries = 3
        embedding = await db_to_use._get_embedding_with_retry(request.text, max_retries)
        await db_to_use.insert(text=request.text, embeddings=embedding)
        logger.info("Data inserted successfully")
        return {"message": "Data inserted successfully"}
    except FlakyNetworkException as error:
        logger.error(
            "Network error during embedding",
            extra={"error": str(error)},
        )
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail="Network error occurred, please try again"
        ) from error
    except ValueError as error:
        logger.error(
            "Error inserting data",
            extra={"error": str(error)},
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(error)
        ) from error
    finally:
        if request.test_db is not None:
            Path.unlink(test_db_path, missing_ok=True)


@app.post("/search", response_model=SearchResponse)
async def search_embeddings(request: SearchRequest) -> SearchResponse:
    """Search for similar embeddings based on the query text.
    
    Args:
        request: The search request containing query text and optional parameters.
        
    Returns:
        SearchResponse containing list of similar results sorted by score.
        
    Raises:
        HTTPException: If search fails due to network or other errors.
    """
    logger.debug(
        "Received search request",
        extra={"query": request.query, "top_k": request.top_k, "use_cache": request.use_cache}
    )
    
    try:
        # Check if we have caching capability
        if hasattr(db, 'search'):
            if hasattr(db, 'cache'):
                # Use cached search
                results = await db.search(
                    query_text=request.query,
                    top_k=request.top_k or 5,
                    use_cache=request.use_cache
                )
            else:
                # Standard search without cache
                results = await db.search(
                    query_text=request.query,
                    top_k=request.top_k or 5
                )
        else:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Search functionality not available"
            )
        
        search_results = [
            SearchResult(id=id_, score=score, text=text)
            for id_, score, text in results
        ]
        
        logger.info(f"Search completed, found {len(search_results)} results")
        
        # Determine if this was a cache hit (simplified check)
        cache_hit = None
        if hasattr(db, 'cache') and request.use_cache:
            # In a real implementation, we'd track this in the search method
            cache_hit = len(results) > 0  # Simplified
        
        return SearchResponse(results=search_results, cache_hit=cache_hit)
        
    except FlakyNetworkException as error:
        logger.error(
            "Network error during search",
            extra={"error": str(error)}
        )
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail="Network error occurred during search, please try again"
        ) from error
    except Exception as error:
        logger.error(
            "Unexpected error during search",
            extra={"error": str(error)}
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        ) from error


@app.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats() -> CacheStats:
    """Get Redis cache statistics.
    
    Returns:
        CacheStats with current cache metrics.
    """
    if hasattr(db, 'cache'):
        stats = await db.cache.get_stats()
        return CacheStats(**stats)
    else:
        return CacheStats(status="disabled")


@app.post("/cache/clear")
async def clear_cache() -> dict[str, str]:
    """Clear all cached search results.
    
    Returns:
        Success message.
    """
    if hasattr(db, 'cache'):
        await db.cache.clear()
        return {"message": "Cache cleared successfully"}
    else:
        raise HTTPException(
            status_code=HTTPStatus.NOT_IMPLEMENTED,
            detail="Cache not available"
        )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Cleanup on shutdown."""
    if hasattr(db, 'close'):
        await db.close()


if __name__ == "__main__":
    """Helper to quickly run the FastAPI application for testing."""
    import socket
    
    def find_available_port(start_port=8000, max_port=9000):
        """Find an available port starting from start_port."""
        for port in range(start_port, max_port):
            try:
                # Try to create a socket on this port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    s.close()
                    return port
            except OSError:
                # Port is in use, try next one
                continue
        raise RuntimeError(f"No available ports found between {start_port} and {max_port}")
    
    # Try default port first, otherwise find an available one
    default_port = int(os.getenv("PORT", 8000))
    
    try:
        # Quick check if default port is available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', default_port))
            s.close()
            port = default_port
    except OSError:
        logger.warning(f"Port {default_port} is already in use, finding an available port...")
        port = find_available_port(default_port + 1)
        logger.info(f"Found available port: {port}")
    
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)