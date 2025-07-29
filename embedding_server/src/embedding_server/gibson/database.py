"""Provides an asynchronous API interaction for a simulated remote vector database."""

import hashlib
import logging
import os
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.DEBUG if "DEBUG" in os.environ else logging.INFO)
logger = logging.getLogger(__name__)


class AsyncEmbeddingDatabase:
    """Provides asynchronous API interaction for a simulated remote vector database."""

    def __init__(self, cache_path: Path):
        """Initializes the asynchronous embedding database.

        Args:
            cache_path: Path to the cache file where the database is stored.
        """
        self.cache_path = cache_path

    async def setup(self) -> None:
        """Asynchronously initializes the database structure."""
        logger.info("Initializing AsyncEmbeddingDatabase, please wait.")

        if self.cache_path and self.cache_path.exists():
            self.data = await self._read_json(self.cache_path)
        else:
            self.data = pd.DataFrame(columns=["ID", "Text", "Embeddings"])
        await self._save()
        logger.info("AsyncEmbeddingDatabase is ready.")

    @staticmethod
    async def _read_json(path: Path) -> pd.DataFrame:
        """Asynchronously reads JSON file.

        Args:
            path: The path to the JSON file to read.

        Returns:
            A pandas DataFrame containing the database data.
        """
        logger.debug(f"Reading JSON file from {path}.")
        return pd.read_json(path)

    async def _save(self) -> None:
        """Saves the database to JSON asynchronously."""
        logger.info(f"Saving database to JSON at {self.cache_path=}.")
        self.data.to_json(self.cache_path, index=False)
        logger.debug("Database saved.")

    async def insert(self, text: str, embeddings: list[float]) -> None:
        """Inserts a new entry into the database asynchronously.

        Args:
            text: The input text corresponding to the embeddings.
            embeddings: The embeddings list to be stored.

        Raises:
            ValueError: If an entry with the generated id already exists or if the embeddings have incorrect dimensions.
        """
        logger.debug(
            "Attempting to insert new entry into the database.", extra={"text": text}
        )

        id_value = hashlib.sha256(text.encode()).hexdigest()

        if self.data["ID"].isin([id_value]).any():
            logger.error(
                "Attempted to insert an entry with an existing id.",
                extra={"id": id_value},
            )
            raise ValueError(f"Entry with id={id_value} already exists in the database")

        if len(embeddings) != 768:
            logger.error(
                "Attempted to insert embeddings with incorrect dimensions.",
                extra={"id": id_value, "dimensions": len(embeddings)},
            )
            raise ValueError("Embeddings must have 768 dimensions")

        self.data = self.data._append(
            {"ID": id_value, "Text": text, "Embeddings": embeddings}, ignore_index=True
        )

        await self._save()
        logger.debug("New entry inserted into the database.", extra={"id": id_value})
