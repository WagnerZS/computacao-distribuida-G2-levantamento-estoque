import hashlib
import json
import sqlite3
from pathlib import Path

from estoque.domain.produto.enitity import Produto, ProdutoLevantamento


class SQLiteStore:
    """Fonte de verdade local da API; Redis é somente cache."""

    def __init__(self, database_path: str, products_path: str) -> None:
        self._database_path = Path(database_path)
        self._products_path = Path(products_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    nome TEXT NOT NULL,
                    cod_barras TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS inventory (
                    product_id INTEGER PRIMARY KEY REFERENCES products(id),
                    quantidade INTEGER NOT NULL CHECK (quantidade >= 0)
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            count = connection.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"]
            if count == 0:
                products = json.loads(self._products_path.read_text(encoding="utf-8"))
                connection.executemany(
                    "INSERT INTO products (id, nome, cod_barras) VALUES (?, ?, ?)",
                    [(item["id"], item["nome"], item["cod_barras"]) for item in products],
                )
            connection.execute(
                "INSERT OR IGNORE INTO metadata (key, value) VALUES ('inventory_version', '0')"
            )

    def list_products(self) -> list[Produto]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, nome, cod_barras FROM products ORDER BY id"
            ).fetchall()
        return [Produto.model_validate(dict(row)) for row in rows]

    def find_product(
        self,
        product_id: int | None = None,
    ) -> Produto | None:
        if product_id is not None:
            where, value = "id = ?", product_id
        else:
            return None
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT id, nome, cod_barras FROM products WHERE {where}", (value,)
            ).fetchone()
        return Produto.model_validate(dict(row)) if row else None

    def catalog_version(self) -> str:
        products = self.list_products()
        raw = json.dumps([item.model_dump() for item in products], sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def inventory_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'inventory_version'"
            ).fetchone()
        return int(row["value"])

    def _bump_inventory_version(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "UPDATE metadata SET value = CAST(value AS INTEGER) + 1 WHERE key = 'inventory_version'"
        )

    def add_readings(self, product_ids: list[int]) -> None:
        with self._connect() as connection:
            for product_id in product_ids:
                connection.execute(
                    "INSERT INTO inventory (product_id, quantidade) VALUES (?, 1) "
                    "ON CONFLICT(product_id) DO UPDATE SET quantidade = quantidade + 1",
                    (product_id,),
                )
            if product_ids:
                self._bump_inventory_version(connection)

    def current_inventory(self) -> list[ProdutoLevantamento]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT p.id, p.nome, p.cod_barras, i.quantidade
                FROM inventory i JOIN products p ON p.id = i.product_id
                WHERE i.quantidade > 0 ORDER BY p.id
                """
            ).fetchall()
        return [
            ProdutoLevantamento(
                produto=Produto(id=row["id"], nome=row["nome"], cod_barras=row["cod_barras"]),
                quantidade=row["quantidade"],
            )
            for row in rows
        ]
