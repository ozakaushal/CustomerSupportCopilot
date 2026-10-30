from typing import TypedDict
from pydantic import BaseModel, Field


# output of the classify step
class RouteResult(BaseModel):
    route: str = Field(description="'kb' for IT support questions, 'chat' for greetings or small talk")


# output of the check steps
class CheckResult(BaseModel):
    enough: bool = Field(description="true if the given text is enough to answer the question")


# data that is passed between all the graph steps
class CopilotState(TypedDict):
    question: str
    search_query: str
    kb_docs: list
    web_context: str
    kb_ok: bool
    web_ok: bool
    rewrites: int
    answer: str
    answered_by: str
    sources: list
    steps: list
