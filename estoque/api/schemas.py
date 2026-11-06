from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from estoque.domain.produto.enitity import Produto, ProdutoLevantamento


class ReadingRequest(BaseModel):
    """Evento enviado pelo Raspberry quando o sensor detecta um item."""

    detected: bool = True
    product_id: int | None = Field(default=None, gt=0)
    barcode: str | None = Field(default=None, min_length=1)
    device_id: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_product_reference(self) -> "ReadingRequest":
        if self.product_id is not None and self.barcode is not None:
            raise ValueError("informe product_id ou barcode, não os dois")
        return self


class InventoryResponse(BaseModel):
    items: list[ProdutoLevantamento]
    total_items: int
    updated_at: datetime | None = None


class ReadingResponse(BaseModel):
    accepted: bool
    product: Produto | None = None
    inventory: InventoryResponse


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: str
    created_at: datetime
    items: list[ProdutoLevantamento]
    total_items: int


class HealthResponse(BaseModel):
    status: str
    redis: str
