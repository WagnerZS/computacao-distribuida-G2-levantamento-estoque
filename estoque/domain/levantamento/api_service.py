import random
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

from estoque.api.schemas import InventoryResponse, ReportResponse
from estoque.config import Settings
from estoque.domain.produto.enitity import Produto, ProdutoLevantamento
from estoque.infra.redis_cache import RedisCache
from estoque.infra.sqlite_store import SQLiteStore


class InventoryService:
    def __init__(self, database: SQLiteStore, cache: RedisCache, settings: Settings) -> None:
        self._database = database
        self._cache = cache
        self._settings = settings

    def find_product(self, product_id: int | None) -> Produto:
        product = self._database.find_product(product_id)
        if product is not None:
            return product
        if product_id is not None:
            raise KeyError(f"produto {product_id} não encontrado")
        products = self._database.list_products()
        if not products:
            raise RuntimeError("catálogo de produtos vazio")
        return random.choice(products)

    @staticmethod
    def _inventory_payload(items: Sequence[ProdutoLevantamento]) -> list[dict[str, Any]]:
        return [item.model_dump() for item in items]

    async def current(self) -> InventoryResponse:
        version = str(self._database.inventory_version())
        key = "estoque:inventory:current"
        cached = await self._cache.get_json(key, version)
        if cached is not None:
            cached_payload = cast(dict[str, Any], cached)
            return InventoryResponse.model_validate(
                {**cached_payload, "source": "cache", "cache_version": version}
            )
        items = self._database.current_inventory()
        payload = {
            "items": self._inventory_payload(items),
            "total_items": sum(item.quantidade for item in items),
            "updated_at": datetime.now(UTC).isoformat() if items else None,
        }
        await self._cache.set_json(key, version, payload)
        return InventoryResponse.model_validate(
            {**payload, "source": "database", "cache_version": version}
        )

    async def register_product_ids(self, product_ids: list[int]) -> InventoryResponse:
        self._database.add_readings(product_ids)
        await self._cache.delete("estoque:inventory:current")
        return await self.current()

    async def submit(self) -> ReportResponse:
        items = self._database.current_inventory()
        report_id, created_at = self._database.save_report(items)
        await self._cache.delete("estoque:inventory:current")
        return ReportResponse(
            report_id=report_id,
            created_at=created_at,
            items=items,
            total_items=sum(item.quantidade for item in items),
        )

    def get_report(self, report_id: str) -> ReportResponse | None:
        data = self._database.get_report(report_id)
        return ReportResponse.model_validate(data) if data else None

    async def products(self) -> list[Produto]:
        version = self._database.catalog_version()
        key = "estoque:products"
        cached = await self._cache.get_json(key, version)
        if cached is not None:
            return [Produto.model_validate(item) for item in cached]
        products = self._database.list_products()
        await self._cache.set_json(key, version, [item.model_dump() for item in products])
        return products
