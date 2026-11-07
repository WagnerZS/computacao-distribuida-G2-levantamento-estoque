import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from estoque.domain.produto.enitity import Produto


class ReaderQueue:
    def __init__(
        self,
        database_path: str,
        products: list[Produto],
        api_url: str,
        device_id: str,
    ) -> None:
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._products = {product.id: product for product in products}
        self._api_url = api_url.rstrip("/")
        self._device_id = device_id
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS pending_readings "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL, "
                "created_at TEXT NOT NULL)"
            )

    def add(self, product: Produto) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO pending_readings (product_id, created_at) VALUES (?, ?)",
                (product.id, datetime.now(UTC).isoformat()),
            )

    def pending_count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM pending_readings").fetchone()[0])

    def pending_items(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, product_id, created_at FROM pending_readings ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def grouped_counts(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT product_id, COUNT(*) AS quantidade FROM pending_readings "
                "GROUP BY product_id ORDER BY product_id"
            ).fetchall()
        return [
            {
                "product": self._products[row["product_id"]].model_dump(),
                "quantidade": row["quantidade"],
            }
            for row in rows
            if row["product_id"] in self._products
        ]

    def delete_ids(self, ids: list[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as connection:
            connection.execute(f"DELETE FROM pending_readings WHERE id IN ({placeholders})", ids)

    async def send(self) -> dict[str, Any]:
        pending = self.pending_items()
        if not pending:
            return {"sent": 0, "pending": 0, "inventory": None}
        payload = {
            "readings": [
                {"product_id": item["product_id"], "device_id": self._device_id} for item in pending
            ]
        }
        async with httpx.AsyncClient(base_url=self._api_url, timeout=10.0) as client:
            response = await client.post("/api/estoque/inventario/leituras/lote", json=payload)
            response.raise_for_status()
            result = response.json()
        self.delete_ids([int(item["id"]) for item in pending])
        return {
            "sent": len(pending),
            "pending": self.pending_count(),
            "inventory": result["inventory"],
        }
