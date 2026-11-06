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
    server_port: int = Field(default=8000, ge=1, le=65535)
    redis_url: str = Field(default="redis://localhost:6379/0", min_length=1)
    redis_report_ttl_seconds: int = Field(default=60 * 60 * 24 * 30, gt=0)
    dir_dados: str = Field(default="estoque/dados/produtos.json", min_length=1)

    # Configurações do cliente serial usado como ponte entre o sensor e a API.
    serial_port: str | None = None
    serial_baudrate: int = Field(default=9600, gt=0)
    serial_timeout_seconds: float = Field(default=1.0, gt=0.0)
    serial_startup_delay_seconds: float = Field(default=2.0, ge=0.0)
    serial_reconnect_delay_seconds: float = Field(default=2.0, ge=0.0)
    api_url: str = Field(default="http://localhost:8000", min_length=1)
