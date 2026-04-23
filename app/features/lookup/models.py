"""Models for ISIN lookup responses."""

from pydantic import BaseModel, ConfigDict, Field


class ISINLookupResponse(BaseModel):
    """Response model for ISIN-to-symbol resolution."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    isin: str = Field(..., description="The ISIN that was resolved")
    symbol: str = Field(..., description="Yahoo Finance ticker symbol (e.g., AAPL)")
    name: str | None = Field(None, description="Short company name")
    long_name: str | None = Field(None, description="Full company name")
    type: str | None = Field(None, description="Instrument type (e.g., EQUITY)")
    exchange: str | None = Field(None, description="Exchange display name (e.g., NasdaqGS)")
