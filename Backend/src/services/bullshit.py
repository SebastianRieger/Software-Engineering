from repositories.bullshit import BullshitRepository


class BullshitService:
    def __init__(self, repository: BullshitRepository | None = None) -> None:
        self.repository = repository or BullshitRepository()

    async def get_phrases(self):
        return await self.repository.get_phrases()
