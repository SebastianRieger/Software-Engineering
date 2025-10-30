import asyncio
import pytest
from app.main import create_app
from httpx import AsyncClient


@pytest.fixture
async def async_client():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
