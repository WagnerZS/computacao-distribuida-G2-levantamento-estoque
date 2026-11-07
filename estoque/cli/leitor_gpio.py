import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, cast

import httpx

from estoque.config import Settings

logger = logging.getLogger(__name__)

SENSOR_PIN_BCM = 17
LED_PIN_BCM = 27
BUZZER_PIN_BCM = 22
GPIO_POLL_INTERVAL_SECONDS = 0.2
API_RETRY_INTERVAL_SECONDS = 2.0


def obstacle_detected(sensor_value: float) -> bool:
    return sensor_value == 0


def start_background_task(
    background_tasks: set[asyncio.Task[None]],
    coroutine: Coroutine[Any, Any, None],
    task_name: str,
) -> None:
    task = asyncio.create_task(coroutine, name=task_name)
    background_tasks.add(task)

    def on_task_done(completed: asyncio.Task[None]) -> None:
        background_tasks.discard(completed)
        if completed.cancelled():
            return
        error = completed.exception()
        if error is not None:
            logger.error(
                "Background task failed: %s",
                completed.get_name(),
                exc_info=(type(error), error, error.__traceback__),
            )

    task.add_done_callback(on_task_done)


async def retry_reading(
    send_reading: Callable[[], Awaitable[bool]],
    retry_interval: float = API_RETRY_INTERVAL_SECONDS,
) -> None:
    while not await send_reading():
        logger.warning("Nova tentativa de envio em %.1f segundos", retry_interval)
        await asyncio.sleep(retry_interval)


async def efeito_scanner(led: Any, buzzer: Any) -> None:
    led.on()
    buzzer.frequency = 2200
    buzzer.value = 0.5
    await asyncio.sleep(0.055)

    led.off()
    buzzer.off()
    await asyncio.sleep(0.035)

    led.on()
    buzzer.frequency = 2700
    buzzer.value = 0.5
    await asyncio.sleep(0.045)

    led.off()
    buzzer.off()
    await asyncio.sleep(0.040)

    led.on()
    await asyncio.sleep(0.050)
    led.off()


async def run(settings: Settings) -> None:
    try:
        from gpiozero import LED, DigitalInputDevice, PWMOutputDevice  # noqa: PLC0415
        from gpiozero.pins.lgpio import LGPIOFactory  # noqa: PLC0415
    except ModuleNotFoundError as error:
        if error.name not in {"gpiozero", "lgpio"}:
            raise
        raise SystemExit(
            "GPIO backend nao esta instalado. No Raspberry Pi OS, instale com "
            "'sudo apt install python3-lgpio'. Para disponibilizar o pacote do sistema "
            "no ambiente uv, recrie o ambiente com 'uv venv --system-site-packages' "
            "e execute 'uv sync'."
        ) from error

    try:
        pin_factory = LGPIOFactory()
    except OSError as error:
        raise SystemExit(
            "Nao foi possivel abrir o GPIO chip. Verifique o backend lgpio e as "
            "permissoes de acesso a /dev/gpiochip."
        ) from error

    async with httpx.AsyncClient(base_url=settings.api_url, timeout=10.0) as client:
        last_detected: bool | None = None
        background_tasks: set[asyncio.Task[None]] = set()

        async def send_reading() -> bool:
            logger.info("Enviando leitura para a API em %s", settings.api_url)
            try:
                response = await client.post(
                    "/api/v1/inventory/readings",
                    json={"detected": True, "device_id": "raspberry-pi-gpio"},
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                logger.error(
                    "Nao foi possivel enviar a leitura para %s: %s",
                    settings.api_url,
                    error,
                )
                return False

            try:
                data = cast(dict[str, Any], response.json())
                if data.get("accepted") is not True:
                    logger.error("A API nao aceitou a leitura: %s", data)
                    return False
                product = cast(dict[str, str], data.get("product") or {})
                inventory = cast(dict[str, int], data["inventory"])
                logger.info(
                    "Leitura registrada | Produto: %s | Quantidade total: %s",
                    product.get("nome", "nao identificado"),
                    inventory["total_items"],
                )
                return True
            except (KeyError, TypeError, ValueError) as error:
                logger.error("Resposta invalida da API ao registrar leitura: %s", error)
                return False

        try:
            with (
                DigitalInputDevice(
                    SENSOR_PIN_BCM,
                    pull_up=True,
                    pin_factory=pin_factory,
                ) as sensor,
                LED(LED_PIN_BCM, pin_factory=pin_factory) as led,
                PWMOutputDevice(
                    BUZZER_PIN_BCM,
                    frequency=2200,
                    initial_value=0,
                    pin_factory=pin_factory,
                ) as buzzer,
            ):
                logger.info(
                    "Leitor GPIO ativo | backend=lgpio | sensor=BCM %s, "
                    "LED=BCM %s, buzzer=BCM %s | API=%s",
                    SENSOR_PIN_BCM,
                    LED_PIN_BCM,
                    BUZZER_PIN_BCM,
                    settings.api_url,
                )
                while True:
                    detected = obstacle_detected(sensor.value)
                    if detected != last_detected:
                        logger.info(
                            "OBSTACULO DETECTADO!"
                            if detected
                            else "CAMINHO LIVRE"
                        )
                    if detected and last_detected is not True:
                        start_background_task(
                            background_tasks,
                            retry_reading(send_reading),
                            "send-inventory-reading",
                        )
                        start_background_task(
                            background_tasks,
                            efeito_scanner(led, buzzer),
                            "scanner-effect",
                        )
                    last_detected = detected
                    await asyncio.sleep(GPIO_POLL_INTERVAL_SECONDS)
        finally:
            for task in background_tasks:
                task.cancel()
            if background_tasks:
                await asyncio.gather(*background_tasks, return_exceptions=True)
            pin_factory.close()


def main() -> None:
    settings = Settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        logger.info("Leitor GPIO encerrado.")


if __name__ == "__main__":
    main()
