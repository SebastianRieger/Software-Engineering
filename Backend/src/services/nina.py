from repositories.nina import NinaRepository
from schemas.nina import NinaWarningsResponse


class NinaService:
    def __init__(self, repository: NinaRepository | None = None) -> None:
        self.repository = repository or NinaRepository()

    async def get_warnings(self, ars: str) -> NinaWarningsResponse:
        return await self.repository.get_warnings(ars=ars)
