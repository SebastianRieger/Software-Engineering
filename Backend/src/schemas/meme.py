from typing import Literal

from pydantic import BaseModel


class MemeItem(BaseModel):
    image_url: str
    title: str
    subreddit: str
    previews: list[str]


class MemeBatchResponse(BaseModel):
    memes: list[MemeItem]
    source: Literal["live", "cache"] = "live"
