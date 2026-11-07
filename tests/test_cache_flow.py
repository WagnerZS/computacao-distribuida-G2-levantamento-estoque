import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from estoque.config import Settings
from estoque.domain.levantamento.api_service import InventoryService
from estoque.infra.sqlite_store import SQLiteStore


class FakeCache:
    def __init__(self) -> None:
        self.payload: Any = None
        self.version: str | None = None
        self.set_calls = 0
        self.delete_calls = 0

    async def get_json(self, _key: str, version: str) -> Any:
        if self.version == version:
            return self.payload
        return None

    async def set_json(self, _key: str, version: str, payload: Any) -> None:
        self.version = version
        self.payload = payload
        self.set_calls += 1

    async def delete(self, *_keys: str) -> None:
        self.version = None
        self.payload = None
        self.delete_calls += 1


def test_batch_rebuilds_cache_and_next_manager_read_uses_it() -> None:
    async def verify() -> None:
        root = Path(__file__).parents[1]
        with TemporaryDirectory() as directory:
            database_path = str(Path(directory) / "inventory.sqlite3")
            database = SQLiteStore(database_path, str(root / "estoque/dados/produtos.json"))
            cache = FakeCache()
            service = InventoryService(database, cache, Settings(database_path=database_path))

            await service.current()
            assert cache.set_calls == 1

            await service.register_product_ids([1, 2])
            assert cache.delete_calls == 1
            assert cache.set_calls == 2

            result = await service.current()
            assert result.source == "cache"
            assert result.total_items == 2
            assert cache.set_calls == 2

    asyncio.run(verify())
