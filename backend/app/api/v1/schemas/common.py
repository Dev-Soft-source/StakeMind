from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, object] | list[object] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse[T](BaseModel):
    data: list[T]
    pagination: PaginationMeta
