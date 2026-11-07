from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas do ambiente ou de um arquivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ESTOQUE_",
        extra="ignore",
    )

    server_host: str = Field(default="0.0.0.0", min_length=1)
    server_port: int = Field(default=5000, ge=1, le=65535)
    redis_url: str = Field(default="redis://localhost:6379/0", min_length=1)
    redis_cache_ttl_seconds: int = Field(default=30, gt=0)
    database_path: str = Field(default="estoque/dados/estoque.sqlite3", min_length=1)
    dir_dados: str = Field(default="estoque/dados/produtos.json", min_length=1)

    # Configurações do cliente serial usado como ponte entre o sensor e a API.
    serial_port: str | None = None
    api_url: str = Field(default="http://localhost:5000", min_length=1)
    reader_host: str = Field(default="0.0.0.0", min_length=1)
    reader_port: int = Field(default=5050, ge=1, le=65535)
    reader_queue_database_path: str = Field(
        default="estoque/dados/leitor-pendente.sqlite3", min_length=1
    )
    reader_device_id: str = Field(default="raspberry-pi-gpio", min_length=1)

    # Configurações do GPIO
    sensor_pin_bcm: int = Field(default=17, ge=0)
    led_pin_bcm: int = Field(default=27, ge=0)
    buzzer_pin_bcm: int = Field(default=22, ge=0)
    min_reading_interval_seconds: float = Field(default=1.0, gt=0)
    