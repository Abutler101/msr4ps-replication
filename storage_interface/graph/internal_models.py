from typing import Any

from pydantic import BaseModel


class QueryResult(BaseModel):
    values: list
    keys: tuple
    summary: Any
