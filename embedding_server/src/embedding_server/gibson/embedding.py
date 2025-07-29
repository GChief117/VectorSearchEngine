"""Provides an asynchronous API interaction for a simulated remote embedding service."""

import asyncio
import logging
import os
import random
from http import HTTPStatus

from httpx import AsyncClient

from embedding_server.gibson.exceptions import FlakyNetworkException

logging.basicConfig(level=logging.DEBUG if "DEBUG" in os.environ else logging.INFO)
logger = logging.getLogger(__name__)


class AsyncEmbeddingService:
    """Provides asynchronous API interaction for a simulated remote embedding service."""

    def __init__(self, flaky_network_rate: float = 0.0025):
        """Initializes the asynchronous embedding service.

        Args:
            flaky_network_rate: The probability of encountering a network error.
        """
        self.embedding_model = None
        self.flaky_network_rate = flaky_network_rate

    async def embed(self, text: str) -> list[float]:
        """Generates an embedding for the given text asynchronously.

        Args:
            text: The input text to generate embeddings for.

        Returns:
            A list representing the sentence embedding.

        Raises:
            FlakyNetworkException: If a simulated network error occurs.
        """
        if random.random() < float(self.flaky_network_rate):
            logger.error("Flaky network error occurred during embedding.")
            raise FlakyNetworkException("Network error occurred")

        logger.debug("Generating embeddings.", extra={"text": text})

        url = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-mpnet-base-v2/pipeline/feature-extraction"

        headers = {
            "Authorization": "Bearer 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",  # trufflehog:ignore This is an API key for an interview, not prod.
        }

        async with AsyncClient() as client:
            response = await client.post(
                url=url, headers=headers, json={"inputs": [text]}
            )

        # HuggingFace may need to initialize
        if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            logger.warning(
                "HuggingFace Embedding API is initializing, waiting for it to be ready."
            )
            await asyncio.sleep(response.json()["estimated_time"] + 1)
            response = await client.post(
                url=url, headers=headers, json={"inputs": [text]}
            )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f"Request failed with status code {response.status_code}")

        data = response.json()[0]

        if not isinstance(data, list) or not all(
            isinstance(item, float) for item in data
        ):
            raise ValueError(
                "Expected a list of floats, but received a different type."
            )

        return data
