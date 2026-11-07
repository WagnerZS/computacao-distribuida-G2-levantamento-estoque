from fastapi import APIRouter, HTTPException, Request, status

from estoque.api.schemas import (
    BatchReadingRequest,
    BatchReadingResponse,
    HealthResponse,
    InventoryResponse,
    ReadingRequest,
    ReadingResponse,
    ReportResponse,
)
from estoque.domain.levantamento.api_service import InventoryService

router = APIRouter(prefix="/api/estoque")


def service(request: Request) -> InventoryService:
    return request.app.state.inventory_service


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok" if request.app.state.redis_cache_ok() else "degraded",
        redis="ok" if request.app.state.redis_cache_ok() else "unavailable",
        database="ok",
    )


@router.get("/produtos")
async def list_products(request: Request):
    return await service(request).products()


@router.get("/inventario", response_model=InventoryResponse)
async def current_inventory(request: Request) -> InventoryResponse:
    return await service(request).current()


@router.post(
    "/inventario/leituras",
    response_model=ReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_reading(payload: ReadingRequest, request: Request) -> ReadingResponse:
    current_service = service(request)
    if not payload.detected:
        return ReadingResponse(accepted=False, inventory=await current_service.current())
    try:
        product = current_service.find_product(payload.product_id)
    except (KeyError, RuntimeError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ReadingResponse(
        accepted=True,
        product=product,
        inventory=await current_service.register_product_ids([product.id]),
    )


@router.post(
    "/inventario/leituras/lote",
    response_model=BatchReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_batch(payload: BatchReadingRequest, request: Request) -> BatchReadingResponse:
    current_service = service(request)
    product_ids: list[int] = []
    for reading in payload.readings:
        if not reading.detected:
            continue
        try:
            product_ids.append(current_service.find_product(reading.product_id).id)
        except (KeyError, RuntimeError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
    return BatchReadingResponse(
        accepted=len(product_ids),
        inventory=await current_service.register_product_ids(product_ids),
    )


@router.post("/inventario/finalizar", response_model=ReportResponse)
async def submit_inventory(request: Request) -> ReportResponse:
    return await service(request).submit()


@router.get("/inventario/relatorios/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, request: Request) -> ReportResponse:
    report = service(request).get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="relatório não encontrado")
    return report
