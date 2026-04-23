"""Lookup service: resolves ISINs to ticker symbols via yfinance Search."""

from ...clients.interface import YFinanceClientInterface
from ...utils.cache.interface import CacheInterface
from ...utils.logger import logger
from .models import ISINLookupResponse


async def resolve_isin(
    isin: str,
    client: YFinanceClientInterface,
    isin_cache: CacheInterface | None = None,
) -> ISINLookupResponse:
    """Resolve an ISIN to a ticker symbol and related metadata.

    Args:
        isin: The ISIN to resolve (e.g., "US0378331005").
        client: The YFinance client to use for upstream calls.
        isin_cache: Optional TTL cache for ISIN resolutions. ISIN→symbol
            mappings are highly stable so a long TTL (default 24 h) is appropriate.

    Returns:
        ISINLookupResponse with the resolved symbol and ticker metadata.

    """
    isin = isin.strip().upper()
    logger.info("lookup.isin.fetch.start", extra={"isin": isin})

    if isin_cache:
        cached = await isin_cache.get(isin)
        if cached is not None:
            logger.info("lookup.isin.fetch.cache.hit", extra={"isin": isin})
            return cached

    ticker_data = await client.get_isin_data(isin)

    result = ISINLookupResponse(
        isin=isin,
        symbol=ticker_data.get("symbol", ""),
        name=ticker_data.get("shortname") or None,
        long_name=ticker_data.get("longname") or None,
        type=ticker_data.get("type") or None,
        exchange=ticker_data.get("exchange") or None,
    )

    logger.info("lookup.isin.fetch.success", extra={"isin": isin, "symbol": result.symbol})

    if isin_cache:
        try:
            await isin_cache.set(isin, result)
        except Exception:
            logger.exception("lookup.isin.set.cache.failed", extra={"isin": isin})

    return result
