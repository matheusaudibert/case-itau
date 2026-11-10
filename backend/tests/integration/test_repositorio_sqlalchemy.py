from collections.abc import Callable

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from estoque.domain.exceptions import ProdutoJaExiste
from estoque.domain.produto import Produto, Status
from estoque.infra.uow import SqlAlchemyUnitOfWork
from tests.unit.saldos import saldos

NovaUow = Callable[[], SqlAlchemyUnitOfWork]


def criar(nova_uow: NovaUow, produto: Produto) -> None:
    with nova_uow() as uow:
        uow.produtos.adicionar(produto)
        uow.commit()


@pytest.fixture
def produto_salvo(nova_uow: NovaUow) -> Produto:
    """P001 com total 100, reservas de 10 e 5, bloqueio de 8 (disponível 77)."""
    produto = Produto("P001", "Teclado mecânico")
    criar(nova_uow, produto)
    with nova_uow() as uow:
        produto = uow.produtos.obter("P001")
        assert produto is not None
        produto.entrada(100)
        produto.reservar(10, "Reserva 001")
        produto.reservar(5, "Reserva 002")
        produto.bloquear(8, "Avaria")
        uow.produtos.salvar(produto)
        uow.commit()
    return produto


def test_salvar_e_carregar_produto_mantem_dados_e_saldos(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    with nova_uow() as uow:
        carregado = uow.produtos.obter("P001")

    assert carregado is not None
    assert carregado.nome == "Teclado mecânico"
    assert saldos(carregado) == (100, 77, 15, 8)
    assert sorted((r.id, r.quantidade, r.motivo, r.status, r.criado_em) for r in carregado.reservas) == sorted(
        (r.id, r.quantidade, r.motivo, r.status, r.criado_em) for r in produto_salvo.reservas
    )
    assert [(b.id, b.quantidade, b.motivo, b.criado_em) for b in carregado.bloqueios] == [
        (b.id, b.quantidade, b.motivo, b.criado_em) for b in produto_salvo.bloqueios
    ]


def test_datas_voltam_do_banco_em_utc(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    with nova_uow() as uow:
        reserva = uow.produtos.obter_reserva(produto_salvo.reservas[0].id)

    assert reserva is not None
    assert reserva.criado_em.utcoffset() is not None
    assert reserva.criado_em == produto_salvo.reservas[0].criado_em


def test_liberacao_persiste_status_e_liberado_em(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    reserva_id = produto_salvo.reservas[0].id
    with nova_uow() as uow:
        produto = uow.produtos.obter("P001")
        assert produto is not None
        produto.liberar_reserva(reserva_id)
        uow.produtos.salvar(produto)
        uow.commit()

    with nova_uow() as uow:
        reserva = uow.produtos.obter_reserva(reserva_id)
        produto = uow.produtos.obter("P001")

    assert reserva is not None and produto is not None
    assert reserva.status is Status.LIBERADO
    assert reserva.liberado_em is not None
    assert len(produto.reservas) == 2
    assert saldos(produto) == (100, 87, 5, 8)


def test_obter_e_listar(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    criar(nova_uow, Produto("P002", "Mouse sem fio"))

    with nova_uow() as uow:
        assert uow.produtos.obter("P999") is None
        assert [p.id for p in uow.produtos.listar()] == ["P001", "P002"]
        assert uow.produtos.obter_bloqueio(produto_salvo.bloqueios[0].id) is not None


def test_rollback_nao_grava_nada(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    with nova_uow() as uow:
        produto = uow.produtos.obter("P001")
        assert produto is not None
        produto.entrada(50)
        produto.reservar(20, "Reserva 003")
        uow.produtos.salvar(produto)
        uow.rollback()

    with nova_uow() as uow:
        carregado = uow.produtos.obter("P001")

    assert carregado is not None
    assert saldos(carregado) == (100, 77, 15, 8)
    assert len(carregado.reservas) == 2


def test_excecao_dentro_do_with_desfaz_a_transacao(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    with pytest.raises(RuntimeError), nova_uow() as uow:
        produto = uow.produtos.obter("P001")
        assert produto is not None
        produto.entrada(50)
        uow.produtos.salvar(produto)
        uow.produtos.listar()  # força o flush do UPDATE antes da falha
        raise RuntimeError("falha no meio")

    with nova_uow() as uow:
        carregado = uow.produtos.obter("P001")
    assert carregado is not None and carregado.total == 100


def test_sem_commit_nada_e_gravado(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    with nova_uow() as uow:
        produto = uow.produtos.obter("P001")
        assert produto is not None
        produto.entrada(50)
        uow.produtos.salvar(produto)

    with nova_uow() as uow:
        carregado = uow.produtos.obter("P001")
    assert carregado is not None and carregado.total == 100


def test_salvar_produto_que_nao_esta_no_banco_levanta_erro(nova_uow: NovaUow) -> None:
    with pytest.raises(LookupError), nova_uow() as uow:
        uow.produtos.salvar(Produto("P999", "Nunca adicionado"))


def test_adicionar_produto_existente_levanta_produto_ja_existe(nova_uow: NovaUow, produto_salvo: Produto) -> None:
    with pytest.raises(ProdutoJaExiste), nova_uow() as uow:
        uow.produtos.adicionar(Produto("P001", "Duplicado"))


def test_chave_estrangeira_esta_ativa(engine: Engine) -> None:
    with pytest.raises(IntegrityError), engine.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO reservas (id, produto_id, quantidade, motivo, status, criado_em) "
                "VALUES ('00000000000000000000000000000001', 'P999', 1, 'PED', 'ATIVO', '2026-01-01')"
            )
        )
