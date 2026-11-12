from estoque.api.schemas import ReadingRequest

def test_reading_without_product_is_valid_for_legacy_sensor() -> None:
    payload = ReadingRequest(device_id="raspberry-pi-01")
    assert payload.detected is True
    assert payload.product_id is None
