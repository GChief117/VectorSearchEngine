"""Fixtures for use across the project."""

import asyncio
import logging
import os
from collections.abc import Iterator

import pytest

logging.basicConfig(level=logging.DEBUG if "DEBUG" in os.environ else logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Pytest fixture that creates an event loop for each test session.

    The loop is set to debug mode to allow detecting non-awaited coroutines.

    """
    with asyncio.Runner(debug=True) as runner:
        loop = runner.get_loop()
        yield loop
