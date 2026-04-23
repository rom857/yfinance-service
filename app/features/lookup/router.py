"""Lookup endpoint definitions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from ...clients.interface import YFinanceClientInterface
from ...dependencies import get_isin_cache, get_yfinance_client
from ...utils.cache.interface import CacheInterface
from .models import ISINLookupResponse
from .service import resolve_isin

router = APIRouter()

_ISIN_REGEX = r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$"

ISINParam = Annotated[
    str,
    Path(
        ...,
        description="International Securities Identification Number (12-character alphanumeric)",
        examples="US0378331005",
        pattern=_ISIN_REGEX,
        min_length=12,
        max_length=12,
        title="ISIN",
    ),
]


@router.get(
    "/isin/{isin}",
    response_model=ISINLookupResponse,
    summary="Resolve an ISIN to a ticker symbol",
    description="Maps an ISIN (International Securities Identification Number) to its Yahoo Finance ticker symbol and basic metadata.",
    operation_id="lookupByISIN",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "isin": "US0378331005",
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "long_name": "Apple Inc.",
                        "type": "EQUITY",
                        "exchange": "NasdaqGS",
                    }
                }
            },
        },
        404: {"description": "No symbol found for the given ISIN"},
        422: {"description": "Validation error (invalid ISIN format)"},
        499: {"description": "Request cancelled by client"},
        500: {"description": "Internal server error"},
        503: {"description": "Upstream timeout"},
    },
)
async def lookup_by_isin(
    request: Request,
    isin: ISINParam,
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)],
    isin_cache: Annotated[CacheInterface, Depends(get_isin_cache)],
) -> ISINLookupResponse:
    """Resolve an ISIN to a Yahoo Finance ticker symbol."""
    no_cache = request.headers.get("Cache-Control") == "no-cache"
    if no_cache:
        return await resolve_isin(isin, client, None)
    return await resolve_isin(isin, client, isin_cache)
