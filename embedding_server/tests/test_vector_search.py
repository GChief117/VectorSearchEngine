"""Tests for vector search functionality."""
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest
import pytest_asyncio
from httpx import AsyncClient

from embedding_server.gibson.exceptions import FlakyNetworkException
from embedding_server.server import app
from embedding_server.vector_search import VectorSearchDatabase


@pytest_asyncio.fixture
async def test_db(tmp_path: Path) -> AsyncGenerator[VectorSearchDatabase, None]:
    """Create a test database with sample data."""
    db_path = tmp_path / "test_embeddings.json"
    db = VectorSearchDatabase(db_path)

    # Create sample data
    sample_data = pd.DataFrame({
        "ID": ["id1", "id2", "id3"],
        "Text": ["Hello world", "Python programming", "Machine learning"],
        "Embeddings": [
            [0.1] * 768,  # Simple embeddings for testing
            [0.2] * 768,
            [0.3] * 768
        ]
    })

    db.data = sample_data
    await db._save()
    await db.setup()

    yield db


@pytest.fixture
def mock_embedding_service() -> Any:
    """Mock embedding service to avoid real API calls."""
    with patch('embedding_server.vector_search.AsyncEmbeddingService') as mock:
        instance = mock.return_value
        # Return a consistent embedding for testing
        instance.embed = AsyncMock(return_value=[0.25] * 768)
        yield instance


class TestVectorSearchDatabase:
    """Test cases for VectorSearchDatabase class."""

    @pytest.mark.asyncio
    async def test_search_basic(self, test_db: VectorSearchDatabase, mock_embedding_service: Any) -> None:
        """Test basic search functionality."""
        test_db.embedding_service = mock_embedding_service

        results = await test_db.search("test query", top_k=2)

        assert len(results) == 2
        assert all(len(result) == 3 for result in results)  # (id, score, text)
        assert results[0][1] >= results[1][1]  # Sorted by score descending

    @pytest.mark.asyncio
    async def test_search_all_results(self, test_db: VectorSearchDatabase, mock_embedding_service: Any) -> None:
        """Test search returns all results when top_k > available results."""
        test_db.embedding_service = mock_embedding_service

        results = await test_db.search("test query", top_k=10)

        assert len(results) == 3  # Only 3 items in test db

    @pytest.mark.asyncio
    async def test_cosine_similarity(self) -> None:
        """Test cosine similarity calculation."""
        db = VectorSearchDatabase(Path("dummy"))

        # Test identical vectors
        vec1 = np.array([1, 0, 0])
        vec2 = np.array([1, 0, 0])
        assert abs(db._cosine_similarity(vec1, vec2) - 1.0) < 1e-6

        # Test orthogonal vectors
        vec3 = np.array([0, 1, 0])
        assert abs(db._cosine_similarity(vec1, vec3)) < 1e-6

        # Test opposite vectors
        vec4 = np.array([-1, 0, 0])
        assert abs(db._cosine_similarity(vec1, vec4) + 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_retry_logic_success(self, test_db: VectorSearchDatabase) -> None:
        """Test retry logic succeeds after initial failures."""
        mock_embed = AsyncMock()
        mock_embed.side_effect = [
            FlakyNetworkException("Network error"),
            FlakyNetworkException("Network error"),
            [0.5] * 768  # Success on third try
        ]

        test_db.embedding_service.embed = mock_embed  # type: ignore[method-assign]

        result = await test_db._get_embedding_with_retry("test", max_retries=3)

        assert result == [0.5] * 768
        assert mock_embed.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_logic_failure(self, test_db: VectorSearchDatabase) -> None:
        """Test retry logic raises exception after max retries."""
        mock_embed = AsyncMock()
        mock_embed.side_effect = FlakyNetworkException("Network error")

        test_db.embedding_service.embed = mock_embed  # type: ignore[method-assign]

        with pytest.raises(FlakyNetworkException):
            await test_db._get_embedding_with_retry("test", max_retries=3)

        assert mock_embed.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, test_db: VectorSearchDatabase) -> None:
        """Test exponential backoff timing."""
        mock_embed = AsyncMock()
        mock_embed.side_effect = [
            FlakyNetworkException("Network error"),
            FlakyNetworkException("Network error"),
            [0.5] * 768
        ]

        test_db.embedding_service.embed = mock_embed  # type: ignore[method-assign]

        with patch('asyncio.sleep') as mock_sleep:
            await test_db._get_embedding_with_retry("test", max_retries=3)

            # Check sleep was called with exponential backoff
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1)  # 2^0
            mock_sleep.assert_any_call(2)  # 2^1


class TestSearchEndpoint:
    """Test cases for the /search endpoint."""

    @pytest.mark.asyncio
    async def test_search_endpoint_success(self, tmp_path: Path, mock_embedding_service: Any) -> None:
        """Test successful search via API endpoint."""
        # Setup test database
        db_path = tmp_path / "test_api_embeddings.json"
        test_data = pd.DataFrame({
            "ID": ["id1", "id2"],
            "Text": ["First document", "Second document"],
            "Embeddings": [[0.1] * 768, [0.9] * 768]
        })
        test_data.to_json(db_path, index=False)

        with patch('embedding_server.server.db_path', db_path):
            with patch('embedding_server.server.db') as mock_db:
                mock_db.search = AsyncMock(return_value=[
                    ("id2", 0.95, "Second document"),
                    ("id1", 0.85, "First document")
                ])

                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.post(
                        "/search",
                        json={"query": "test search", "top_k": 2}
                    )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["score"] > data["results"][1]["score"]

    @pytest.mark.asyncio
    async def test_search_endpoint_network_error(self) -> None:
        """Test search endpoint handles network errors."""
        with patch('embedding_server.server.db.search') as mock_search:
            mock_search.side_effect = FlakyNetworkException("Network error")

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/search",
                    json={"query": "test search"}
                )

        assert response.status_code == 503
        assert "Network error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_search_endpoint_default_top_k(self) -> None:
        """Test search endpoint uses default top_k value."""
        with patch('embedding_server.server.db.search') as mock_search:
            mock_search.return_value = []

            async with AsyncClient(app=app, base_url="http://test") as client:
                await client.post(
                    "/search",
                    json={"query": "test search"}  # No top_k specified
                )

            mock_search.assert_called_once_with(
                query_text="test search",
                top_k=5  # Default value
            )
