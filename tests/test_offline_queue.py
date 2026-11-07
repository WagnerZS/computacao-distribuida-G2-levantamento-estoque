from pathlib import Path

from estoque.domain.produto.repository import ProdutoRepository
from estoque.infra.reader_queue import ReaderQueue
from estoque.infra.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]
PRODUCTS = str(ROOT / "estoque/dados/produtos.json")


def test_sqlite_inventory_is_persistent_and_versioned(tmp_path: Path) -> None:
    store = SQLiteStore(str(tmp_path / "estoque.db"), PRODUCTS)
    assert store.inventory_version() == 0
    store.add_readings([1, 1, 2])
    assert store.inventory_version() == 1
    items = store.current_inventory()
    assert [(item.produto.id, item.quantidade) for item in items] == [(1, 2), (2, 1)]


def test_reader_queue_survives_api_failure(tmp_path: Path) -> None:
    products = ProdutoRepository(PRODUCTS).listar()
    queue = ReaderQueue(str(tmp_path / "reader.db"), products, "http://127.0.0.1:1", "test")
    queue.add(products[0])
    queue.add(products[0])
    assert queue.pending_count() == 2
    assert queue.grouped_counts()[0]["quantidade"] == 2
