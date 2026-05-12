from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/contracts", tags=["contracts"])


class PaginationQuery:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="1-based page index")] = 1,
        page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
        sort: Annotated[str, Query(description="Sort direction for list endpoints")] = "desc",
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.sort = sort


@router.get(
    "/pagination",
    response_model=PaginatedResponse[str],
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
    summary="Pagination contract",
    description="Reference shape for versioned list endpoints. Returns an empty page.",
)
async def pagination_contract(
    pagination: Annotated[PaginationQuery, Depends()],
) -> PaginatedResponse[str]:
    return PaginatedResponse(
        data=[],
        pagination=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=0,
            total_pages=0,
        ),
    )
