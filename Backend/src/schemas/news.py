from typing import Literal

from pydantic import BaseModel, Field


class NewsTeaserImage(BaseModel):
    imageVariants: dict[str, str] | None = None
    alttext: str | None = None


class NewsItem(BaseModel):
    sophoraId: str
    title: str
    topline: str | None = None
    firstSentence: str | None = None
    date: str | None = None
    shareURL: str | None = None
    detailsweb: str | None = None
    ressort: str | None = None
    breakingNews: bool | None = None
    teaserImage: NewsTeaserImage | None = None


class NewsResponse(BaseModel):
    news: list[NewsItem] = Field(default_factory=list)
    source: Literal["live", "cache"] = "live"
