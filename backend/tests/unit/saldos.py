from estoque.domain.produto import Produto


def saldos(produto: Produto) -> tuple[int, int, int, int]:
    """(total, disponivel, reservado, bloqueado)"""
    return produto.total, produto.disponivel, produto.reservado, produto.bloqueado
