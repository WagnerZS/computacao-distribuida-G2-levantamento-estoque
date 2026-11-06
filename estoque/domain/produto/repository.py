import json
from pathlib import Path

from estoque.domain.produto.enitity import Produto


class ProdutoRepository:
    def __init__(self, path: str) -> None:
        self._path = Path(path)

    # Carrega os dados de produtos.json, valida de acordo com a classe modelo e retorna objeto
    def listar(self) -> list[Produto]:
        with self._path.open("r", encoding="utf-8") as file:
            dados = json.load(file)

        return [Produto.model_validate(produto) for produto in dados]
