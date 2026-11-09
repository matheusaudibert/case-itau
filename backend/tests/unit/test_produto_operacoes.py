from collections.abc import Callable

import pytest

from estoque.domain.exceptions import EstoqueInsuficiente, QuantidadeInvalida
from estoque.domain.produto import Produto, Status
from tests.unit.saldos import saldos

QUANTIDADES_INVALIDAS = [0, -1, -100, 1.5, 5.0, "5", None, True]

OPERACOES: dict[str, Callable[[Produto, object], object]] = {
    "entrada": lambda p, qtd: p.entrada(qtd),
    "saida": lambda p, qtd: p.saida(qtd),
    "reservar": lambda p, qtd: p.reservar(qtd, "Reserva X"),
    "bloquear": lambda p, qtd: p.bloquear(qtd, "Avaria"),
}

OPERACOES_LIMITADAS_AO_DISPONIVEL = ["saida", "reservar", "bloquear"]


def test_saldos_iniciais_da_fixture(produto: Produto) -> None:
    assert saldos(produto) == (100, 77, 15, 8)


def test_entrada_aumenta_total_e_disponivel(produto: Produto) -> None:
    produto.entrada(20)

    assert saldos(produto) == (120, 97, 15, 8)


def test_saida_reduz_total_e_disponivel_sem_tocar_reservas_e_bloqueios(produto: Produto) -> None:
    produto.saida(7)

    assert saldos(produto) == (93, 70, 15, 8)


def test_saida_de_todo_o_disponivel_zera_o_disponivel(produto: Produto) -> None:
    produto.saida(77)

    assert saldos(produto) == (23, 0, 15, 8)


def test_reservar_cria_reserva_ativa_e_reduz_disponivel(produto: Produto) -> None:
    reserva = produto.reservar(12, "Reserva 003")

    assert reserva.produto_id == "P001"
    assert reserva.quantidade == 12
    assert reserva.motivo == "Reserva 003"
    assert reserva.status is Status.ATIVO
    assert reserva.liberado_em is None
    assert reserva in produto.reservas
    assert saldos(produto) == (100, 65, 27, 8)


def test_bloquear_cria_bloqueio_ativo_e_reduz_disponivel(produto: Produto) -> None:
    bloqueio = produto.bloquear(4, "Inventário")

    assert bloqueio.produto_id == "P001"
    assert bloqueio.quantidade == 4
    assert bloqueio.motivo == "Inventário"
    assert bloqueio.status is Status.ATIVO
    assert bloqueio.liberado_em is None
    assert bloqueio in produto.bloqueios
    assert saldos(produto) == (100, 73, 15, 12)


def test_bloquear_sem_motivo_e_permitido(produto: Produto) -> None:
    bloqueio = produto.bloquear(1)

    assert bloqueio.motivo is None


def test_varias_reservas_e_bloqueios_do_mesmo_produto_somam_nos_saldos() -> None:
    produto = Produto("P002", "Mouse")
    produto.entrada(50)

    produto.reservar(10, "Reserva A")
    produto.reservar(10, "Reserva A")
    produto.bloquear(5)
    produto.bloquear(5)

    assert saldos(produto) == (50, 20, 20, 10)
    assert len({r.id for r in produto.reservas}) == 2


@pytest.mark.parametrize("operacao", OPERACOES_LIMITADAS_AO_DISPONIVEL)
def test_operacao_com_exatamente_o_disponivel_e_permitida(produto: Produto, operacao: str) -> None:
    OPERACOES[operacao](produto, 77)

    assert produto.disponivel == 0


@pytest.mark.parametrize("operacao", OPERACOES_LIMITADAS_AO_DISPONIVEL)
def test_operacao_acima_do_disponivel_levanta_estoque_insuficiente(produto: Produto, operacao: str) -> None:
    with pytest.raises(EstoqueInsuficiente) as erro:
        OPERACOES[operacao](produto, 78)

    assert erro.value.solicitado == 78
    assert erro.value.disponivel == 77


@pytest.mark.parametrize("operacao", OPERACOES_LIMITADAS_AO_DISPONIVEL)
def test_operacao_acima_do_disponivel_mas_abaixo_do_total_levanta_estoque_insuficiente(
    produto: Produto, operacao: str
) -> None:
    """O total é 100, mas 23 unidades estão presas em reservas e bloqueios."""
    with pytest.raises(EstoqueInsuficiente):
        OPERACOES[operacao](produto, 100)


@pytest.mark.parametrize("operacao", OPERACOES)
@pytest.mark.parametrize("qtd", QUANTIDADES_INVALIDAS)
def test_quantidade_invalida_levanta_quantidade_invalida(produto: Produto, operacao: str, qtd: object) -> None:
    with pytest.raises(QuantidadeInvalida):
        OPERACOES[operacao](produto, qtd)


CASOS_INVALIDOS = [(op, qtd) for op in OPERACOES for qtd in QUANTIDADES_INVALIDAS] + [
    (op, qtd) for op in OPERACOES_LIMITADAS_AO_DISPONIVEL for qtd in (78, 1000)
]


@pytest.mark.parametrize(("operacao", "qtd"), CASOS_INVALIDOS)
def test_operacao_invalida_nao_altera_saldos_nem_cria_registros(
    produto: Produto, operacao: str, qtd: object
) -> None:
    antes = saldos(produto)
    reservas_antes = len(produto.reservas)
    bloqueios_antes = len(produto.bloqueios)

    with pytest.raises((QuantidadeInvalida, EstoqueInsuficiente)):
        OPERACOES[operacao](produto, qtd)

    assert saldos(produto) == antes
    assert len(produto.reservas) == reservas_antes
    assert len(produto.bloqueios) == bloqueios_antes


def test_reservar_sem_motivo_e_permitido(produto: Produto) -> None:
    reserva = produto.reservar(1)

    assert reserva.motivo is None
    assert saldos(produto) == (100, 76, 16, 8)


def test_saida_em_produto_sem_estoque_levanta_estoque_insuficiente() -> None:
    produto = Produto("P002", "Mouse")

    with pytest.raises(EstoqueInsuficiente):
        produto.saida(1)
