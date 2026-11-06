import json
import random
from datetime import UTC, datetime
from uuid import uuid4

from redis.asyncio import Redis

from estoque.api.schemas import InventoryResponse, ReportResponse
from estoque.config import Settings
from estoque.domain.produto.enitity import Produto, ProdutoLevantamento

INVENTORY_KEY = "estoque:inventory:current"
UPDATED_AT_KEY = "estoque:inventory:updated_at"
EVENTS_KEY = "estoque:inventory:events"
REPORT_KEY_PREFIX = "estoque:inventory:reports:"
LOCK_NAME = "estoque:inventory:lock"


class InventoryService:
    def __init__(self, redis: Redis, products: list[Produto], settings: Settings) -> None:
        self._redis = redis
        self._products = products
        self._settings = settings
        self._by_id = {product.id: product for product in products}
        self._by_barcode = {product.cod_barras: product for product in products}

    def find_product(self, product_id: int | None, barcode: str | None) -> Produto:
        if product_id is not None and product_id not in self._by_id:
            raise KeyError(f"produto {product_id} não encontrado")
        if barcode is not None and barcode not in self._by_barcode:
            raise KeyError(f"código de barras {barcode} não encontrado")
        if product_id is not None:
            return self._by_id[product_id]
        if barcode is not None:
            return self._by_barcode[barcode]
        return random.choice(self._products)

    async def current(self) -> InventoryResponse:
        quantities = await self._redis.hgetall(INVENTORY_KEY)
        items = [
            ProdutoLevantamento(produto=self._by_id[int(product_id)], quantidade=int(quantity))
            for product_id, quantity in quantities.items()
            if int(quantity) > 0
        ]
        items.sort(key=lambda item: item.produto.id)
        updated = await self._redis.get(UPDATED_AT_KEY)
        updated_at = datetime.fromisoformat(str(updated)) if updated else None
        return InventoryResponse(
            items=items,
            total_items=sum(item.quantidade for item in items),
            updated_at=updated_at,
        )

    async def register_reading(self, product: Produto, device_id: str | None) -> InventoryResponse:
        async with self._redis.lock(LOCK_NAME, timeout=10, blocking_timeout=5):
            await self._redis.hincrby(INVENTORY_KEY, str(product.id), 1)
            now = datetime.now(UTC)
            await self._redis.set(UPDATED_AT_KEY, now.isoformat())
            await self._redis.xadd(
                EVENTS_KEY,
                {
                    "type": "reading",
                    "product_id": str(product.id),
                    "device_id": device_id or "unknown",
                    "at": now.isoformat(),
                },
                maxlen=10000,
                approximate=True,
            )
            return await self.current()

    async def submit(self) -> ReportResponse:
        async with self._redis.lock(LOCK_NAME, timeout=10, blocking_timeout=5):
            inventory = await self.current()
            report = ReportResponse(
                report_id=str(uuid4()),
                created_at=datetime.now(UTC),
                items=inventory.items,
                total_items=inventory.total_items,
            )
            await self._redis.set(
                REPORT_KEY_PREFIX + report.report_id,
                report.model_dump_json(),
                ex=self._settings.redis_report_ttl_seconds,
            )
            await self._redis.xadd(
                EVENTS_KEY,
                {
                    "type": "submitted",
                    "report_id": report.report_id,
                    "total_items": str(report.total_items),
                    "at": report.created_at.isoformat(),
                },
                maxlen=10000,
                approximate=True,
            )
            await self._redis.delete(INVENTORY_KEY, UPDATED_AT_KEY)
            return report

    async def get_report(self, report_id: str) -> ReportResponse | None:
        value = await self._redis.get(REPORT_KEY_PREFIX + report_id)
        return ReportResponse.model_validate(json.loads(value)) if value else None
