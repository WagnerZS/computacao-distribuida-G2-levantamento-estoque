import uvicorn

from estoque.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "estoque.api.app:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
