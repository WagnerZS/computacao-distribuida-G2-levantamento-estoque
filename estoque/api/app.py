from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from estoque.api.routes import router
from estoque.config import Settings
from estoque.domain.levantamento.api_service import InventoryService
from estoque.infra.redis_cache import RedisCache
from estoque.infra.sqlite_store import SQLiteStore


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    manager_path = Path(__file__).resolve().parents[1] / "web" / "manager"

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        redis = Redis.from_url(app_settings.redis_url, decode_responses=True)
        database = SQLiteStore(app_settings.database_path, app_settings.dir_dados)
        cache = RedisCache(redis, app_settings.redis_cache_ttl_seconds)
        app.state.redis = redis
        app.state.database = database
        app.state.inventory_service = InventoryService(database, cache, app_settings)
        app.state.redis_cache_ok = lambda: False
        try:
            app.state.redis_cache_ok = lambda: bool(app.state.redis_last_ping)
            app.state.redis_last_ping = await cache.ping()
            yield
        finally:
            await redis.aclose()

    application = FastAPI(
        title="Levantamento de Estoque API",
        version="2.1.0",
        description="API REST com SQLite como base e Redis como cache.",
        lifespan=lifespan,
    )
    application.mount(
        "/manager-static",
        StaticFiles(directory=str(manager_path)),
        name="manager-static",
    )

    @application.get("/manager", response_class=FileResponse)
    async def manager_index() -> str:
        return str(manager_path / "index.html")

    application.include_router(router)
    return application


app = create_app()
