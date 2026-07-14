"""Valuation API (Phase 48) — a transparent DCF with editable assumptions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.db.database import get_db
from src.valuation import service

router = APIRouter(prefix="/valuation", tags=["valuation"])


class DcfOverrides(BaseModel):
    growth_rate: float | None = Field(None, ge=-0.5, le=1.0)
    terminal_growth: float | None = Field(None, ge=0, le=0.06)
    discount_rate: float | None = Field(None, ge=0.03, le=0.30)
    years: int | None = Field(None, ge=3, le=10)


@router.get("/dcf/{ticker}")
def dcf(ticker: str) -> dict:
    """A DCF with assumptions anchored to the company's filed cash-flow history."""
    result = service.valuation(get_db(), ticker)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"No filed cash-flow data to value {ticker.upper()}."
        )
    return result


@router.post("/dcf/{ticker}")
def dcf_custom(ticker: str, overrides: DcfOverrides) -> dict:
    """Re-run the DCF with the user's own assumptions."""
    result = service.valuation(
        get_db(), ticker, overrides.model_dump(exclude_none=True)
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data to value {ticker.upper()}.")
    return result


class ScreenFilter(BaseModel):
    field: str
    op: str = Field(pattern=r"^(>|>=|<|<=)$")
    value: float


class ScreenRequest(BaseModel):
    filters: list[ScreenFilter] = Field(default_factory=list, max_length=6)
    universe: list[str] | None = None


@router.get("/screener/fields")
def screener_fields() -> dict:
    from src.valuation.screener import FIELDS

    return {"fields": list(FIELDS)}


@router.post("/screener")
def run_screener(body: ScreenRequest) -> dict:
    """Filter the covered universe by filed fundamentals — deterministic, no LLM SQL."""
    from src.valuation import screener

    return screener.screen(
        get_db(),
        [f.model_dump() for f in body.filters],
        universe=body.universe,
    )
