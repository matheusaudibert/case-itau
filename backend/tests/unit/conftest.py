import pytest

from estoque.domain.produto import Produto


@pytest.fixture
def produto() -> Produto:
    """Produto com total 100, reservado 15, bloqueado 8 e disponível 77."""
    produto = Produto("P001", "Teclado mecânico")
    produto.entrada(100)
    produto.reservar(10, "Reserva 001")
    produto.reservar(5, "Reserva 002")
    produto.bloquear(8, "Avaria")
    return produto
