from repositories.meme import MemeRepository


class MemeService:
    def __init__(self, repository: MemeRepository | None = None) -> None:
        self.repository = repository or MemeRepository()

    async def get_memes(self, subreddit: str = "memes", sfw_only: bool = True):
        return await self.repository.get_memes(subreddit=subreddit, sfw_only=sfw_only)
