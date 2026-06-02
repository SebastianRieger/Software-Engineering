from typing import Literal

from pydantic import BaseModel


class TriviaQuestion(BaseModel):
    question: str
    correct_answer: str
    answers: list[str]
    category: str
    difficulty: Literal["easy", "medium", "hard"]
    type: Literal["multiple", "boolean"]
    source: Literal["live", "cache"] = "live"
