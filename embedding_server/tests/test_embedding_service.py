"""Tests basic functionality of the embedding service and database."""

import asyncio
import json
import logging
import os
from pathlib import Path

import aiofiles
import pytest

from embedding_server.gibson.database import AsyncEmbeddingDatabase
from embedding_server.gibson.embedding import AsyncEmbeddingService

logging.basicConfig(level=logging.DEBUG if "DEBUG" in os.environ else logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_async_insert(tmp_path: Path) -> None:
    """Tests the asynchronous insertion of embeddings into the database.

    This test checks if embeddings generated from text are correctly inserted into an asynchronous
    embedding database. It involves setting up a mock embedding service and embedding database, inserting
    a known text to check the embedding's shape, and inserting multiple texts from a file.

    Args:
        tmp_path: A pathlib.Path object provided by the pytest framework for creating temporary files and directories.
    """
    logger.debug("Setting up AsyncEmbeddingService and AsyncEmbeddingDatabase.")
    embedding_service = AsyncEmbeddingService(flaky_network_rate=0.0)
    embedding_database = AsyncEmbeddingDatabase(cache_path=tmp_path / "testdb.json")
    await embedding_database.setup()

    async def embed_and_insert(text: str) -> None:
        """Embeds a given text using embedding service and inserts it into the database.

        It fetches the embedding for a given text asynchronously and then inserts the text
        and its embedding into the database.

        Args:
            text: The text to embed and insert into the database.
        """
        embedding = await embedding_service.embed(text=text)
        await embedding_database.insert(text=text, embeddings=embedding)

    logger.debug("Reading sentences from file.")
    async with aiofiles.open(
        Path(__file__).parent.parent / "data" / "sentences.txt", "r", encoding="utf-8"
    ) as file:
        data_content = await file.read()
        data = data_content.splitlines()[0:10]

    counter: int = 0
    logger.debug("Inserting known text for embedding shape verification.")
    embedding = await embedding_service.embed("I want to go to there!")

    assert isinstance(embedding, list), "Expected embedding to be a list."
    assert len(embedding) == 768, "Expected embedding length to be 768."

    await embedding_database.insert(text="I want to go to there!", embeddings=embedding)
    counter += 1

    tasks = [embed_and_insert(text) for text in data]
    await asyncio.gather(*tasks)
    counter += len(tasks)

    logger.debug("Verifying the insertion into the database by counting entries.")
    async with aiofiles.open(tmp_path / "testdb.json", "r", encoding="utf-8") as file:
        json_content = json.loads(await file.read())
        assert (
            len(json_content["ID"]) == counter
        ), "Mismatch in the number of inserted IDs."
        assert (
            len(json_content["Text"]) == counter
        ), "Mismatch in the number of inserted Texts."
        assert (
            len(json_content["Embeddings"]) == counter
        ), "Mismatch in the number of inserted Embeddings."
