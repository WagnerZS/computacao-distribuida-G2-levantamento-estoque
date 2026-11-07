from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from estoque.domain.produto.enitity import Produto, ProdutoLevantamento


class ReadingRequest(BaseModel):
    detected: bool = True
    product_id: int | None = Field(default=None, gt=0)
    device_id: str | None = Field(default=None, min_length=1, max_length=100)

class BatchReadingRequest(BaseModel):
    readings: list[ReadingRequest] = Field(min_length=1, max_length=5000)


class InventoryResponse(BaseModel):
    items: list[ProdutoLevantamento]
    total_items: int
    updated_at: datetime | None = None
    source: Literal["cache", "database"] = "database"
    cache_version: str | None = None


class ReadingResponse(BaseModel):
    accepted: bool
    product: Produto | None = None
    inventory: InventoryResponse


class BatchReadingResponse(BaseModel):
    accepted: int
    inventory: InventoryResponse


class ReportResponse(BaseModel):
    report_id: str
    created_at: datetime
    items: list[ProdutoLevantamento]
    total_items: int


class HealthResponse(BaseModel):
    status: str
    redis: str
    database: str
