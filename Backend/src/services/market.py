from repositories.market import MarketRepository


class MarketService:
    def __init__(self, repository: MarketRepository | None = None):
        self.repository = repository or MarketRepository()

    async def get_market(self, symbols: list[str]):
        return await self.repository.get_market(symbols)
