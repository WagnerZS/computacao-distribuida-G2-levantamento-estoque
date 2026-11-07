import asyncio

from estoque.cli import leitor_gpio


class FakeGPIO:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events

    def on(self) -> None:
        self.events.append(("on",))

    def off(self) -> None:
        self.events.append(("off",))


class FakeBuzzer:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self.events = events

    @property
    def frequency(self) -> int:
        return 0

    @frequency.setter
    def frequency(self, frequency: int) -> None:
        self.events.append(("frequency", frequency))

    @property
    def value(self) -> float:
        return 0

    @value.setter
    def value(self, duty_cycle: float) -> None:
        self.events.append(("value", duty_cycle))

    def on(self) -> None:
        self.events.append(("on",))

    def off(self) -> None:
        self.events.append(("off",))


def test_gpio_pins_match_documented_bcm_assignment() -> None:
    assert leitor_gpio.SENSOR_PIN_BCM == 17
    assert leitor_gpio.LED_PIN_BCM == 27
    assert leitor_gpio.BUZZER_PIN_BCM == 22


def test_sensor_value_zero_means_obstacle() -> None:
    assert leitor_gpio.obstacle_detected(0)
    assert not leitor_gpio.obstacle_detected(1)


def test_reading_retries_until_api_accepts(monkeypatch) -> None:
    outcomes = iter([False, False, True])
    attempts = 0
    delays: list[float] = []

    async def send_reading() -> bool:
        nonlocal attempts
        attempts += 1
        return next(outcomes)

    async def fake_sleep(duration: float) -> None:
        delays.append(duration)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    asyncio.run(leitor_gpio.retry_reading(send_reading, retry_interval=2.0))

    assert attempts == 3
    assert delays == [2.0, 2.0]


def test_background_task_failure_does_not_stop_sensor_loop(caplog) -> None:
    async def verify() -> None:
        background_tasks: set[asyncio.Task[None]] = set()
        sensor_loop_ticks = 0

        async def fail() -> None:
            raise RuntimeError("simulated send failure")

        leitor_gpio.start_background_task(
            background_tasks,
            fail(),
            "simulated-send",
        )
        await asyncio.sleep(0)
        sensor_loop_ticks += 1
        await asyncio.sleep(0)

        assert sensor_loop_ticks == 1
        assert not background_tasks

    asyncio.run(verify())
    assert "Background task failed: simulated-send" in caplog.text


def test_scanner_effect_matches_sketch_timing_and_tones(monkeypatch) -> None:
    events: list[tuple[object, ...]] = []
    led = FakeGPIO(events)

    async def fake_sleep(duration: float) -> None:
        events.append(("sleep", duration))

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    asyncio.run(leitor_gpio.efeito_scanner(led, FakeBuzzer(events)))

    assert events == [
        ("on",),
        ("frequency", 2200),
        ("value", 0.5),
        ("sleep", 0.055),
        ("off",),
        ("off",),
        ("sleep", 0.035),
        ("on",),
        ("frequency", 2700),
        ("value", 0.5),
        ("sleep", 0.045),
        ("off",),
        ("off",),
        ("sleep", 0.040),
        ("on",),
        ("sleep", 0.050),
        ("off",),
    ]
