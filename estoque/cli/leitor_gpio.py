import asyncio
import logging
import random
import time
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

from gpiozero import LED, DigitalInputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

from uvicorn import Config, Server

from estoque.cli.reader_server import ReaderController, create_reader_app
from estoque.config import Settings
from estoque.domain.produto.repository import ProdutoRepository
from estoque.infra.reader_queue import ReaderQueue

logger = logging.getLogger(__name__)

settings = Settings()

def obstacle_detected(sensor_value: float) -> bool:
    return sensor_value == 0


def reading_allowed(detected: bool, now: float, last_reading_at: float) -> bool:
    return detected and now - last_reading_at >= settings.min_reading_interval_seconds


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


async def resposta_produto_detectado(led: Any, buzzer: Any) -> None:
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
        pin_factory = LGPIOFactory(chip=0)
    except OSError as error:
        raise SystemExit(
            "Não foi possível abrir o GPIO chip. Verifique o backend lgpio e "
            "as permissões de /dev/gpiochip."
        ) from error

    products = ProdutoRepository(settings.dir_dados).listar()
    queue = ReaderQueue(
        settings.reader_queue_database_path,
        products,
        settings.api_url,
        settings.reader_device_id,
    )
    controller = ReaderController(
        queue, str(Path(__file__).resolve().parents[1] / "web" / "index.html")
    )
    web_server = Server(
        Config(
            create_reader_app(controller),
            host=settings.reader_host,
            port=settings.reader_port,
            log_level="warning",
        )
    )
    web_task = asyncio.create_task(web_server.serve(), name="ReaderWebServer")
    background_tasks: set[asyncio.Task[None]] = set()
    sensor_events: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    try:
        with (
            DigitalInputDevice(
                settings.sensor_pin_bcm,
                pull_up=None,
                active_state=False,
                pin_factory=pin_factory,
            ) as sensor,
            LED(settings.led_pin_bcm, pin_factory=pin_factory) as led,
            PWMOutputDevice(
                settings.buzzer_pin_bcm,
                frequency=2200,
                initial_value=0,
                pin_factory=pin_factory,
            ) as buzzer,
        ):
            logger.info(
                "Leitor GPIO ativo | sensor=BCM %s | active_state=False | LED=BCM %s | "
                "buzzer=BCM %s | tela=http://0.0.0.0:%s",
                settings.sensor_pin_bcm,
                settings.led_pin_bcm,
                settings.buzzer_pin_bcm,
                settings.reader_port,
            )

            def detectar() -> None:
                loop.call_soon_threadsafe(sensor_events.put_nowait, "activated")

            def remover() -> None:
                loop.call_soon_threadsafe(sensor_events.put_nowait, "deactivated")

            sensor.when_activated = detectar
            sensor.when_deactivated = remover

            last_reading_at = 0.0
            while True:
                try:
                    event = await sensor_events.get()
                    now = time.time()
                    if event == "deactivated" or now - last_reading_at < settings.min_reading_interval_seconds:
                        continue
                    product = random.choice(products)
                    await asyncio.to_thread(queue.add, product)
                    last_reading_at = now
                    pending = await asyncio.to_thread(queue.pending_count)
                    logger.info(
                        "Objeto detectado pelo KY-032 | produto sorteado=%s | pendentes=%s",
                        product.nome,
                        pending,
                    )
                    start_background_task(
                        background_tasks,
                        resposta_produto_detectado(led, buzzer),
                        "scanner-effect",
                    )
                except Exception:
                    logger.exception("Falha no evento do leitor;")
    finally:
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
        web_server.should_exit = True
        await web_task
        pin_factory.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        logger.info("Leitor GPIO encerrado.")


if __name__ == "__main__":
    main()
    