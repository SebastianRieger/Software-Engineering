from fastapi import APIRouter, Depends, HTTPException, Query

from repositories.market import MarketRepositoryError
from schemas.market import MarketResponse
from services.market import MarketService

router = APIRouter()


async def get_market_service() -> MarketService:
    return MarketService()


@router.get("", response_model=MarketResponse)
@router.get("/", response_model=MarketResponse, include_in_schema=False)
async def get_market(
    symbols: str = Query(
        ..., description="Comma-separated list of symbols (e.g. AAPL,BTC%2FUSD)"
    ),
    market_service: MarketService = Depends(get_market_service),
):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=422, detail="At least one symbol is required.")
    try:
        return await market_service.get_market(symbol_list)
    except MarketRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
