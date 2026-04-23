"""Fixtures for lookup feature tests."""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture(scope="function")
def isin_payload_factory():
    """Factory for fake get_isin_data() return values."""
    base = {
        "symbol": "AAPL",
        "shortname": "Apple Inc.",
        "longname": "Apple Inc.",
        "type": "EQUITY",
        "exchange": "NasdaqGS",
    }

    def _factory(**overrides):
        payload = base.copy()
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture(scope="function")
def failing_cache():
    c = AsyncMock()
    c.get.return_value = None
    c.set.side_effect = Exception("Cache failure")
    return c
