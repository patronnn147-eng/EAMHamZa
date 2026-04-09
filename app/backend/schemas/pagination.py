from typing import Generic, List, TypeVar
import math
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        if size <= 0:
            size = 100
        total_pages = math.ceil(total / size)
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
