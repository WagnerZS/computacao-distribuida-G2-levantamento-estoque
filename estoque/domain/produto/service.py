import json
from pathlib import Path

from redis.asyncio import Redis

from estoque.domain.produto.enitity import Produto

PRODUCTS_CACHE_KEY = "estoque:products"


class ProductService:
    def __init__(self, data_path: str, redis: Redis) -> None:
        self._data_path = Path(data_path)
        self._redis = redis

    async def load(self) -> list[Produto]:
        cached = await self._redis.get(PRODUCTS_CACHE_KEY)
        if cached:
            return [Produto.model_validate(item) for item in json.loads(cached)]

        with self._data_path.open("r", encoding="utf-8") as file:
            products = [Produto.model_validate(item) for item in json.load(file)]
        await self._redis.set(
            PRODUCTS_CACHE_KEY,
            json.dumps([product.model_dump() for product in products], ensure_ascii=False),
        )
        return products
