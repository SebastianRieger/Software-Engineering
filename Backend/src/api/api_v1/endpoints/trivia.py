from fastapi import APIRouter, Depends, HTTPException

from repositories.trivia import TriviaRepositoryError
from schemas.trivia import TriviaQuestion
from services.trivia import TriviaService

router = APIRouter()


async def get_trivia_service() -> TriviaService:
    return TriviaService()


@router.get("", response_model=TriviaQuestion)
@router.get("/", response_model=TriviaQuestion, include_in_schema=False)
async def get_trivia(
    trivia_service: TriviaService = Depends(get_trivia_service),
):
    try:
        return await trivia_service.get_question()
    except TriviaRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
