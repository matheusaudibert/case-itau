from uuid import uuid4

import pytest

from estoque.domain.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)
from estoque.domain.produto import Produto, Status
from tests.unit.saldos import saldos


def reserva_com_motivo(produto: Produto, motivo: str):
    return next(r for r in produto.reservas if r.motivo == motivo)


def test_liberar_reserva_devolve_quantidade_ao_disponivel(produto: Produto) -> None:
    reserva = reserva_com_motivo(produto, "Reserva 001")

    produto.liberar_reserva(reserva.id)

    assert saldos(produto) == (100, 87, 5, 8)


def test_liberar_reserva_muda_status_e_grava_liberado_em_sem_apagar(produto: Produto) -> None:
    reserva = reserva_com_motivo(produto, "Reserva 001")

    liberada = produto.liberar_reserva(reserva.id)

    assert liberada is reserva
    assert reserva.status is Status.LIBERADO
    assert reserva.liberado_em is not None
    assert reserva.liberado_em >= reserva.criado_em
    assert reserva in produto.reservas


def test_liberar_reserva_nao_afeta_as_demais(produto: Produto) -> None:
    produto.liberar_reserva(reserva_com_motivo(produto, "Reserva 001").id)

    outra = reserva_com_motivo(produto, "Reserva 002")
    assert outra.status is Status.ATIVO
    assert outra.liberado_em is None


def test_liberar_bloqueio_devolve_quantidade_ao_disponivel(produto: Produto) -> None:
    bloqueio = produto.bloqueios[0]

    liberado = produto.liberar_bloqueio(bloqueio.id)

    assert liberado is bloqueio
    assert bloqueio.status is Status.LIBERADO
    assert bloqueio.liberado_em is not None
    assert bloqueio in produto.bloqueios
    assert saldos(produto) == (100, 85, 15, 0)


def test_liberar_reserva_inexistente_levanta_reserva_nao_encontrada(produto: Produto) -> None:
    antes = saldos(produto)

    with pytest.raises(ReservaNaoEncontrada):
        produto.liberar_reserva(uuid4())

    assert saldos(produto) == antes


def test_liberar_bloqueio_inexistente_levanta_bloqueio_nao_encontrado(produto: Produto) -> None:
    antes = saldos(produto)

    with pytest.raises(BloqueioNaoEncontrado):
        produto.liberar_bloqueio(uuid4())

    assert saldos(produto) == antes


def test_liberar_id_de_bloqueio_como_reserva_levanta_reserva_nao_encontrada(produto: Produto) -> None:
    with pytest.raises(ReservaNaoEncontrada):
        produto.liberar_reserva(produto.bloqueios[0].id)


def test_liberar_reserva_de_outro_produto_levanta_reserva_nao_encontrada(produto: Produto) -> None:
    outro = Produto("P002", "Mouse")
    outro.entrada(10)
    reserva_de_outro = outro.reservar(1, "Reserva X")

    with pytest.raises(ReservaNaoEncontrada):
        produto.liberar_reserva(reserva_de_outro.id)


def test_liberar_reserva_duas_vezes_levanta_reserva_ja_liberada(produto: Produto) -> None:
    reserva = reserva_com_motivo(produto, "Reserva 001")
    produto.liberar_reserva(reserva.id)
    liberado_em = reserva.liberado_em
    antes = saldos(produto)

    with pytest.raises(ReservaJaLiberada):
        produto.liberar_reserva(reserva.id)

    assert saldos(produto) == antes
    assert reserva.liberado_em == liberado_em


def test_liberar_bloqueio_duas_vezes_levanta_bloqueio_ja_liberado(produto: Produto) -> None:
    bloqueio = produto.bloqueios[0]
    produto.liberar_bloqueio(bloqueio.id)
    liberado_em = bloqueio.liberado_em
    antes = saldos(produto)

    with pytest.raises(BloqueioJaLiberado):
        produto.liberar_bloqueio(bloqueio.id)

    assert saldos(produto) == antes
    assert bloqueio.liberado_em == liberado_em


def test_quantidade_liberada_pode_ser_reservada_novamente(produto: Produto) -> None:
    produto.liberar_reserva(reserva_com_motivo(produto, "Reserva 001").id)

    produto.reservar(87, "Reserva 003")

    assert saldos(produto) == (100, 0, 92, 8)


def test_reconstituir_produto_com_reservas_e_bloqueios_recalcula_saldos(produto: Produto) -> None:
    copia = Produto(
        produto.id,
        produto.nome,
        total=produto.total,
        reservas=produto.reservas,
        bloqueios=produto.bloqueios,
    )

    assert saldos(copia) == saldos(produto)
