import random

from estoque.domain.produto.enitity import Produto, ProdutoLevantamento


class LevantamentoService:
    def __init__(self, produtos: list[Produto]) -> None:
        self._produtos = produtos
        self._levantamento: list[ProdutoLevantamento] = []

    def registrar_leitura(self) -> Produto:
        produto = random.choice(self._produtos)

        for item in self._levantamento:
            if item.produto.id == produto.id:
                item.quantidade += 1
                return produto

        self._levantamento.append(
            ProdutoLevantamento(
                produto=produto,
                quantidade=1,
            )
        )

        return produto

    def obter_levantamento(self) -> list[ProdutoLevantamento]:
        return self._levantamento.copy()

    def limpar_levantamento(self) -> None:
        self._levantamento.clear()
