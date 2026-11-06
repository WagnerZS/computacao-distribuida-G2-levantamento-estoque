from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from estoque.api.routes import router
from estoque.config import Settings
from estoque.domain.levantamento.service_v2 import InventoryService
from estoque.domain.produto.service import ProductService


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        redis: Redis = Redis.from_url(app_settings.redis_url, decode_responses=True)
        await redis.ping()
        product_service = ProductService(app_settings.dir_dados, redis)
        products = await product_service.load()
        app.state.redis = redis
        app.state.product_service = product_service
        app.state.inventory_service = InventoryService(redis, products, app_settings)
        try:
            yield
        finally:
            await redis.aclose()

    application = FastAPI(
        title="Levantamento de Estoque API",
        version="2.0.0",
        description="API REST para o levantamento de estoque com Raspberry, FastAPI e Redis.",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
