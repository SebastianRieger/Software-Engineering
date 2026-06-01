from fastapi import APIRouter, Depends, HTTPException

from repositories.bullshit import BullshitRepositoryError
from schemas.bullshit import BullshitResponse
from services.bullshit import BullshitService

router = APIRouter()


async def get_bullshit_service() -> BullshitService:
    return BullshitService()


@router.get("", response_model=BullshitResponse)
@router.get("/", response_model=BullshitResponse, include_in_schema=False)
async def get_bullshit(
    bullshit_service: BullshitService = Depends(get_bullshit_service),
):
    try:
        return await bullshit_service.get_phrases()
    except BullshitRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
