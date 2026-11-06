from fastapi import APIRouter, HTTPException, Request, status

from estoque.api.schemas import (
    HealthResponse,
    InventoryResponse,
    ReadingRequest,
    ReadingResponse,
    ReportResponse,
)
from estoque.domain.levantamento.service_v2 import InventoryService

router = APIRouter(prefix="/api/v1")


def inventory_service(request: Request) -> InventoryService:
    return request.app.state.inventory_service


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    try:
        await request.app.state.redis.ping()
        return HealthResponse(status="ok", redis="ok")
    except Exception:
        return HealthResponse(status="degraded", redis="unavailable")


@router.get("/products")
async def list_products(request: Request):
    return await request.app.state.product_service.load()


@router.get("/inventory", response_model=InventoryResponse)
async def current_inventory(request: Request) -> InventoryResponse:
    return await inventory_service(request).current()


@router.post(
    "/inventory/readings",
    response_model=ReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_reading(payload: ReadingRequest, request: Request) -> ReadingResponse:
    service = inventory_service(request)
    if not payload.detected:
        return ReadingResponse(accepted=False, inventory=await service.current())
    try:
        product = service.find_product(payload.product_id, payload.barcode)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ReadingResponse(
        accepted=True,
        product=product,
        inventory=await service.register_reading(product, payload.device_id),
    )


@router.post("/inventory/submit", response_model=ReportResponse)
async def submit_inventory(request: Request) -> ReportResponse:
    return await inventory_service(request).submit()


@router.get("/inventory/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, request: Request) -> ReportResponse:
    report = await inventory_service(request).get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="relatório não encontrado ou expirado")
    return report
