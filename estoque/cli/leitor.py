import asyncio
import logging
from typing import Any, cast

import httpx

from estoque.config import Settings
from estoque.infra.input.serial.source import SerialInputSource

logger = logging.getLogger(__name__)


async def run(settings: Settings) -> None:
    async with httpx.AsyncClient(base_url=settings.api_url, timeout=10.0) as client:

        async def on_reading(_: bool) -> None:
            try:
                response = await client.post(
                    "/api/v1/inventory/readings",
                    json={"detected": True, "device_id": settings.serial_port or "serial"},
                )
                response.raise_for_status()
                data = cast(dict[str, Any], response.json())
                product = cast(dict[str, str], data.get("product") or {})
                inventory = cast(dict[str, int], data["inventory"])
                logger.info(
                    "Leitura registrada | Produto: %s | Quantidade total: %s",
                    product.get("nome", "não identificado"),
                    inventory["total_items"],
                )
            except httpx.HTTPError as error:
                logger.error("Não foi possível enviar a leitura para a API: %s", error)

        def callback(value: bool) -> None:
            asyncio.create_task(on_reading(value))

        source = SerialInputSource(settings=settings, on_update=callback)
        await source.start()
        try:
            await asyncio.Event().wait()
        finally:
            await source.stop()


def main() -> None:
    settings = Settings()
    if not settings.serial_port:
        raise SystemExit("Defina ESTOQUE_SERIAL_PORT para executar o leitor serial.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        logger.info("Leitor encerrado.")


if __name__ == "__main__":
    main()
