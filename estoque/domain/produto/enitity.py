from pydantic import BaseModel


class Produto(BaseModel):
    id: int
    nome: str
    cod_barras: str


class ProdutoLevantamento(BaseModel):
    produto: Produto
    quantidade: int
