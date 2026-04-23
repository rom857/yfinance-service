"""Tests for the `/lookup/isin/{isin}` endpoint."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.features.lookup.models import ISINLookupResponse
from app.features.lookup.service import resolve_isin
from app.utils.cache.ttl_in_memory import TTLCache

VALID_ISIN = "US0378331005"  # Apple
INVALID_ISIN = "NOTANISIN"


# ---------------------------------------------------------------------------
# HTTP endpoint tests (use global `client` + `mock_yfinance_client` fixtures)
# ---------------------------------------------------------------------------


def test_lookup_valid_isin(client, mock_yfinance_client, isin_payload_factory):
    """Valid ISIN returns resolved symbol and metadata."""
    mock_yfinance_client.get_isin_data.return_value = isin_payload_factory()

    resp = client.get(f"/lookup/isin/{VALID_ISIN}")
    assert resp.status_code == 200

    data = ISINLookupResponse.model_validate(resp.json())
    assert data.isin == VALID_ISIN
    assert data.symbol == "AAPL"
    assert data.name == "Apple Inc."
    assert data.exchange == "NasdaqGS"


def test_lookup_invalid_isin_format_returns_422(client):
    """An ISIN that fails the regex pattern returns 422 without calling the client."""
    resp = client.get(f"/lookup/isin/{INVALID_ISIN}")
    assert resp.status_code == 422


def test_lookup_isin_too_short_returns_422(client):
    """An ISIN that is too short returns 422."""
    resp = client.get("/lookup/isin/US037833100")  # 11 chars
    assert resp.status_code == 422


def test_lookup_isin_lowercase_returns_422(client):
    """Lowercase ISIN does not match the uppercase-only regex and returns 422."""
    resp = client.get("/lookup/isin/us0378331005")
    assert resp.status_code == 422


def test_lookup_isin_not_found(client, mock_yfinance_client):
    """When client raises 404, the endpoint propagates it."""
    mock_yfinance_client.get_isin_data.side_effect = HTTPException(
        status_code=404, detail="No symbol found for ISIN: US0378331005"
    )

    resp = client.get(f"/lookup/isin/{VALID_ISIN}")
    assert resp.status_code == 404
    assert "No symbol found" in resp.json()["detail"]


def test_lookup_no_cache_header_bypasses_cache(client, mock_yfinance_client, isin_payload_factory):
    """Cache-Control: no-cache header bypasses the cache and always calls the client."""
    mock_yfinance_client.get_isin_data.return_value = isin_payload_factory()

    client.get(f"/lookup/isin/{VALID_ISIN}")
    client.get(f"/lookup/isin/{VALID_ISIN}", headers={"Cache-Control": "no-cache"})

    assert mock_yfinance_client.get_isin_data.call_count == 2


# ---------------------------------------------------------------------------
# Service unit tests (direct, no HTTP layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_isin_returns_response(fake_yfinance_client):
    """resolve_isin returns an ISINLookupResponse with the fake client's data."""
    result = await resolve_isin(VALID_ISIN, fake_yfinance_client, isin_cache=None)

    assert isinstance(result, ISINLookupResponse)
    assert result.isin == VALID_ISIN
    assert result.symbol == "FAKE"
    assert result.name == "Fake Company Inc."


@pytest.mark.asyncio
async def test_resolve_isin_uses_cache_hit():
    """When a cached result exists, resolve_isin returns it without calling the client."""
    cache = TTLCache(size=4, ttl=60)
    cached = ISINLookupResponse(
        isin=VALID_ISIN,
        symbol="AAPL",
        name="Apple Inc.",
        long_name="Apple Inc.",
        type="EQUITY",
        exchange="NasdaqGS",
    )
    await cache.set(VALID_ISIN, cached)

    mock_client = AsyncMock()
    result = await resolve_isin(VALID_ISIN, mock_client, isin_cache=cache)

    assert result is cached
    mock_client.get_isin_data.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_isin_stores_in_cache(fake_yfinance_client):
    """After a successful resolution the result is stored in the cache."""
    cache = TTLCache(size=4, ttl=60)

    await resolve_isin(VALID_ISIN, fake_yfinance_client, isin_cache=cache)

    cached = await cache.get(VALID_ISIN)
    assert cached is not None
    assert cached.symbol == "FAKE"


@pytest.mark.asyncio
async def test_resolve_isin_cache_set_failure_does_not_raise(
    fake_yfinance_client, failing_cache
):
    """A cache write failure is logged but does not propagate to the caller."""
    result = await resolve_isin(VALID_ISIN, fake_yfinance_client, isin_cache=failing_cache)
    assert result.symbol == "FAKE"


@pytest.mark.asyncio
async def test_resolve_isin_strips_and_uppercases_input():
    """ISIN is normalised (stripped and uppercased) before lookup."""
    mock_client = AsyncMock()
    mock_client.get_isin_data.return_value = {
        "symbol": "AAPL",
        "shortname": "Apple Inc.",
        "longname": "Apple Inc.",
        "type": "EQUITY",
        "exchange": "NasdaqGS",
    }

    result = await resolve_isin("  us0378331005  ", mock_client, isin_cache=None)
    called_with = mock_client.get_isin_data.call_args[0][0]
    assert called_with == "US0378331005"
    assert result.isin == "US0378331005"
