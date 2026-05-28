from repositories.news import NewsRepository


class NewsService:
    def __init__(self, repository: NewsRepository | None = None):
        self.repository = repository or NewsRepository()

    async def get_news(
        self,
        ressort: str | None = None,
        regions: list[int] | None = None,
    ):
        return await self.repository.get_news(ressort=ressort, regions=regions)
