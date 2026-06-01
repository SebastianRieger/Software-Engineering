from repositories.fact import FactRepository


class FactService:
    def __init__(self, repository: FactRepository | None = None) -> None:
        self.repository = repository or FactRepository()

    async def get_fact(self):
        return await self.repository.get_fact()
