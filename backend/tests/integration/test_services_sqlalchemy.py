from uuid import uuid4

import pytest

from estoque.application.services import ServicoEstoque
from estoque.domain.exceptions import (
    EstoqueInsuficiente,
    ProdutoJaExiste,
    ProdutoNaoEncontrado,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)
from estoque.domain.produto import Status
from tests.unit.saldos import saldos


@pytest.fixture
def servico_com_produto(servico: ServicoEstoque) -> ServicoEstoque:
    servico.criar_produto("P001", "Teclado mecânico")
    return servico


def test_fluxo_entrada_reservar_bloquear_e_liberar(servico_com_produto: ServicoEstoque) -> None:
    servico = servico_com_produto

    servico.entrada("P001", 100)
    reserva = servico.reservar("P001", 10, "Reserva 001")
    servico.reservar("P001", 5, "Reserva 002")
    bloqueio = servico.bloquear("P001", 8, "Avaria")
    assert saldos(servico.consultar_produto("P001")) == (100, 77, 15, 8)

    liberada = servico.liberar_reserva(reserva.id)
    servico.liberar_bloqueio(bloqueio.id)

    assert liberada.status is Status.LIBERADO
    assert saldos(servico.consultar_produto("P001")) == (100, 95, 5, 0)
    assert servico.consultar_reserva(reserva.id).status is Status.LIBERADO
    assert [r.motivo for r in servico.listar_reservas("P001", Status.ATIVO)] == ["Reserva 002"]
    assert [b.id for b in servico.listar_bloqueios("P001", Status.LIBERADO)] == [bloqueio.id]


def test_saida_persiste(servico_com_produto: ServicoEstoque) -> None:
    servico_com_produto.entrada("P001", 10)
    servico_com_produto.saida("P001", 4)

    assert saldos(servico_com_produto.consultar_produto("P001")) == (6, 6, 0, 0)


def test_erro_de_dominio_nao_altera_o_banco(servico_com_produto: ServicoEstoque) -> None:
    servico_com_produto.entrada("P001", 10)

    with pytest.raises(EstoqueInsuficiente):
        servico_com_produto.reservar("P001", 11, "Reserva 001")

    produto = servico_com_produto.consultar_produto("P001")
    assert saldos(produto) == (10, 10, 0, 0)
    assert produto.reservas == []


def test_erros_de_nao_encontrado_e_duplicidade(servico_com_produto: ServicoEstoque) -> None:
    with pytest.raises(ProdutoNaoEncontrado):
        servico_com_produto.entrada("P999", 1)
    with pytest.raises(ReservaNaoEncontrada):
        servico_com_produto.liberar_reserva(uuid4())
    with pytest.raises(ProdutoJaExiste):
        servico_com_produto.criar_produto("P001", "Duplicado")


def test_liberar_reserva_duas_vezes(servico_com_produto: ServicoEstoque) -> None:
    servico_com_produto.entrada("P001", 10)
    reserva = servico_com_produto.reservar("P001", 3, "Reserva 001")
    servico_com_produto.liberar_reserva(reserva.id)

    with pytest.raises(ReservaJaLiberada):
        servico_com_produto.liberar_reserva(reserva.id)
