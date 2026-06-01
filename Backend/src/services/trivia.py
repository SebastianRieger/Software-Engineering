from repositories.trivia import TriviaRepository


class TriviaService:
    def __init__(self, repository: TriviaRepository | None = None) -> None:
        self.repository = repository or TriviaRepository()

    async def get_question(self):
        return await self.repository.get_question()
