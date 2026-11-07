import asyncio
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from estoque.infra.reader_queue import ReaderQueue


class ReaderController:
    def __init__(self, queue: ReaderQueue, web_path: str) -> None:
        self.queue = queue
        self.web_path = web_path
        self.last_send: dict[str, Any] | None = None

    async def status(self) -> dict[str, Any]:
        pending, items = await asyncio.gather(
            asyncio.to_thread(self.queue.pending_count),
            asyncio.to_thread(self.queue.grouped_counts),
        )
        return {
            "pending": pending,
            "items": items,
            "last_send": self.last_send,
        }

    async def send(self) -> dict[str, Any]:
        try:
            result = await self.queue.send()
        except httpx.HTTPError as error:
            raise HTTPException(
                status_code=503,
                detail="API indisponível; as leituras continuam na fila local.",
            ) from error
        self.last_send = result
        return {**result, "status": await self.status()}


def create_reader_app(controller: ReaderController) -> FastAPI:
    application = FastAPI(title="Leitor GPIO", version="2.1.0")
    web_path = Path(controller.web_path)

    @application.get("/static/styles.css")
    async def styles() -> FileResponse:
        return FileResponse(web_path.parent / "static" / "styles.css", media_type="text/css")

    @application.get("/static/app.js")
    async def script() -> FileResponse:
        return FileResponse(web_path.parent / "static" / "app.js", media_type="text/javascript")

    application.mount(
        "/static",
        StaticFiles(directory=str(web_path.parent / "static")),
        name="reader-static",
    )

    @application.get("/", response_class=FileResponse)
    async def index() -> str:
        return controller.web_path

    @application.get("/api/reader/status")
    async def status() -> dict[str, Any]:
        return await controller.status()

    @application.post("/api/reader/send")
    async def send() -> dict[str, Any]:
        return await controller.send()

    return application
