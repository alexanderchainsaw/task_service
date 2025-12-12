from pydantic import BaseModel


class PaginationParams(BaseModel):
    limit: int = 20
    offset: int = 0
