import pytest
from pydantic import ValidationError

from estoque.api.schemas import ReadingRequest
from estoque.infra.input.serial.parser import LeitorParser


def test_sensor_parser_accepts_only_detection_signal() -> None:
    parser = LeitorParser()
    assert parser.feed_line("1\n") is True
    assert parser.feed_line("0\n") is False


def test_reading_cannot_receive_two_product_references() -> None:
    with pytest.raises(ValidationError):
        ReadingRequest(product_id=1, barcode="7891000100011")


def test_reading_without_product_is_valid_for_legacy_sensor() -> None:
    payload = ReadingRequest(device_id="raspberry-pi-01")
    assert payload.detected is True
    assert payload.product_id is None
