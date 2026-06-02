from fastapi import APIRouter, Depends, HTTPException

from repositories.fact import FactRepositoryError
from schemas.fact import DailyFact
from services.fact import FactService

router = APIRouter()


async def get_fact_service() -> FactService:
    return FactService()


@router.get("", response_model=DailyFact)
@router.get("/", response_model=DailyFact, include_in_schema=False)
async def get_fact(
    fact_service: FactService = Depends(get_fact_service),
):
    try:
        return await fact_service.get_fact()
    except FactRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
