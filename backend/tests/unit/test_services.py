from collections.abc import Callable
from uuid import uuid4

import pytest

from estoque.application.services import MAX_TENTATIVAS, ServicoEstoque
from estoque.domain.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    ConflitoDeConcorrencia,
    EstoqueInsuficiente,
    IdProdutoInvalido,
    ProdutoJaExiste,
    ProdutoNaoEncontrado,
    QuantidadeInvalida,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)
from estoque.domain.produto import Produto, Status
from tests.unit.fakes import BancoEmMemoria, UnitOfWorkEmMemoria
from tests.unit.saldos import saldos


@pytest.fixture
def banco() -> BancoEmMemoria:
    banco = BancoEmMemoria()
    produto = Produto("P001", "Teclado mecânico")
    produto.entrada(100)
    banco.inserir(produto)
    banco.inserir(Produto("P002", "Mouse sem fio"))
    return banco


@pytest.fixture
def servico(banco: BancoEmMemoria) -> ServicoEstoque:
    return ServicoEstoque(lambda: UnitOfWorkEmMemoria(banco))


def persistido(banco: BancoEmMemoria, produto_id: str = "P001") -> Produto:
    return banco.produtos[produto_id]


# --- caminho de sucesso ---------------------------------------------------


def test_criar_produto_persiste_produto_com_saldos_zerados(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    produto = servico.criar_produto("P003", "Monitor")

    assert produto.id == "P003"
    assert saldos(persistido(banco, "P003")) == (0, 0, 0, 0)
    assert banco.commits == 1


def test_listar_produtos_devolve_todos(servico: ServicoEstoque) -> None:
    assert [p.id for p in servico.listar_produtos()] == ["P001", "P002"]


def test_consultar_produto_devolve_saldos(servico: ServicoEstoque) -> None:
    assert saldos(servico.consultar_produto("P001")) == (100, 100, 0, 0)


def test_entrada_persiste_novo_total(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    produto = servico.entrada("P002", 50)

    assert produto.total == 50
    assert persistido(banco, "P002").total == 50


def test_saida_persiste_novo_total(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    servico.saida("P001", 30)

    assert saldos(persistido(banco)) == (70, 70, 0, 0)


def test_reservar_persiste_reserva_ativa(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    reserva = servico.reservar("P001", 10, "Reserva 001")

    assert reserva.status is Status.ATIVO
    assert reserva.motivo == "Reserva 001"
    assert saldos(persistido(banco)) == (100, 90, 10, 0)


def test_bloquear_persiste_bloqueio_ativo(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    bloqueio = servico.bloquear("P001", 8, "Avaria")

    assert bloqueio.status is Status.ATIVO
    assert bloqueio.motivo == "Avaria"
    assert saldos(persistido(banco)) == (100, 92, 0, 8)


def test_liberar_reserva_persiste_status_liberado(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    reserva = servico.reservar("P001", 10, "Reserva 001")

    liberada = servico.liberar_reserva(reserva.id)

    assert liberada.status is Status.LIBERADO
    assert liberada.liberado_em is not None
    assert saldos(persistido(banco)) == (100, 100, 0, 0)


def test_liberar_bloqueio_persiste_status_liberado(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    bloqueio = servico.bloquear("P001", 8)

    liberado = servico.liberar_bloqueio(bloqueio.id)

    assert liberado.status is Status.LIBERADO
    assert saldos(persistido(banco)) == (100, 100, 0, 0)


def test_consultar_reserva_e_bloqueio_por_id(servico: ServicoEstoque) -> None:
    reserva = servico.reservar("P001", 10, "Reserva 001")
    bloqueio = servico.bloquear("P001", 8)

    assert servico.consultar_reserva(reserva.id).quantidade == 10
    assert servico.consultar_bloqueio(bloqueio.id).quantidade == 8


def test_listar_reservas_filtra_por_status(servico: ServicoEstoque) -> None:
    primeira = servico.reservar("P001", 10, "Reserva 001")
    segunda = servico.reservar("P001", 5, "Reserva 002")
    servico.liberar_reserva(primeira.id)

    todas = servico.listar_reservas("P001")
    ativas = servico.listar_reservas("P001", Status.ATIVO)
    liberadas = servico.listar_reservas("P001", Status.LIBERADO)

    assert [r.id for r in todas] == [primeira.id, segunda.id]
    assert [r.id for r in ativas] == [segunda.id]
    assert [r.id for r in liberadas] == [primeira.id]


def test_listar_bloqueios_filtra_por_status(servico: ServicoEstoque) -> None:
    primeiro = servico.bloquear("P001", 3)
    segundo = servico.bloquear("P001", 4)
    servico.liberar_bloqueio(segundo.id)

    assert [b.id for b in servico.listar_bloqueios("P001")] == [primeiro.id, segundo.id]
    assert [b.id for b in servico.listar_bloqueios("P001", Status.ATIVO)] == [primeiro.id]


# --- erros ----------------------------------------------------------------

OPERACOES_POR_PRODUTO: dict[str, Callable[[ServicoEstoque, str], object]] = {
    "consultar_produto": lambda s, pid: s.consultar_produto(pid),
    "entrada": lambda s, pid: s.entrada(pid, 1),
    "saida": lambda s, pid: s.saida(pid, 1),
    "reservar": lambda s, pid: s.reservar(pid, 1, "Reserva X"),
    "bloquear": lambda s, pid: s.bloquear(pid, 1),
    "listar_reservas": lambda s, pid: s.listar_reservas(pid),
    "listar_bloqueios": lambda s, pid: s.listar_bloqueios(pid),
}


@pytest.mark.parametrize("operacao", OPERACOES_POR_PRODUTO)
def test_produto_inexistente_levanta_produto_nao_encontrado(servico: ServicoEstoque, operacao: str) -> None:
    with pytest.raises(ProdutoNaoEncontrado):
        OPERACOES_POR_PRODUTO[operacao](servico, "P999")


def test_criar_produto_com_id_existente_levanta_produto_ja_existe(
    servico: ServicoEstoque, banco: BancoEmMemoria
) -> None:
    with pytest.raises(ProdutoJaExiste):
        servico.criar_produto("P001", "Outro nome")

    assert persistido(banco).nome == "Teclado mecânico"


def test_criar_produto_com_id_invalido_nao_abre_transacao(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    with pytest.raises(IdProdutoInvalido):
        servico.criar_produto("p001", "Teclado")

    assert banco.transacoes == 0


def test_liberar_reserva_inexistente_levanta_reserva_nao_encontrada(servico: ServicoEstoque) -> None:
    with pytest.raises(ReservaNaoEncontrada):
        servico.liberar_reserva(uuid4())


def test_liberar_bloqueio_inexistente_levanta_bloqueio_nao_encontrado(servico: ServicoEstoque) -> None:
    with pytest.raises(BloqueioNaoEncontrado):
        servico.liberar_bloqueio(uuid4())


def test_consultar_reserva_e_bloqueio_inexistentes(servico: ServicoEstoque) -> None:
    with pytest.raises(ReservaNaoEncontrada):
        servico.consultar_reserva(uuid4())
    with pytest.raises(BloqueioNaoEncontrado):
        servico.consultar_bloqueio(uuid4())


def test_liberar_reserva_duas_vezes_levanta_reserva_ja_liberada(servico: ServicoEstoque) -> None:
    reserva = servico.reservar("P001", 10, "Reserva 001")
    servico.liberar_reserva(reserva.id)

    with pytest.raises(ReservaJaLiberada):
        servico.liberar_reserva(reserva.id)


def test_liberar_bloqueio_duas_vezes_levanta_bloqueio_ja_liberado(servico: ServicoEstoque) -> None:
    bloqueio = servico.bloquear("P001", 8)
    servico.liberar_bloqueio(bloqueio.id)

    with pytest.raises(BloqueioJaLiberado):
        servico.liberar_bloqueio(bloqueio.id)


# --- commit e rollback ----------------------------------------------------

OPERACOES_DE_ESCRITA: dict[str, Callable[[ServicoEstoque], object]] = {
    "criar_produto": lambda s: s.criar_produto("P003", "Monitor"),
    "entrada": lambda s: s.entrada("P001", 1),
    "saida": lambda s: s.saida("P001", 1),
    "reservar": lambda s: s.reservar("P001", 1, "Reserva X"),
    "bloquear": lambda s: s.bloquear("P001", 1),
}


@pytest.mark.parametrize("operacao", OPERACOES_DE_ESCRITA)
def test_operacao_de_escrita_com_sucesso_faz_commit_sem_rollback(
    servico: ServicoEstoque, banco: BancoEmMemoria, operacao: str
) -> None:
    OPERACOES_DE_ESCRITA[operacao](servico)

    assert (banco.commits, banco.rollbacks) == (1, 0)


@pytest.mark.parametrize(
    ("operacao", "erro"),
    [
        (lambda s: s.entrada("P001", 0), QuantidadeInvalida),
        (lambda s: s.saida("P001", 101), EstoqueInsuficiente),
        (lambda s: s.reservar("P001", 101, "Reserva X"), EstoqueInsuficiente),
        (lambda s: s.bloquear("P001", -1), QuantidadeInvalida),
        (lambda s: s.entrada("P999", 1), ProdutoNaoEncontrado),
        (lambda s: s.liberar_reserva(uuid4()), ReservaNaoEncontrada),
        (lambda s: s.criar_produto("P001", "Duplicado"), ProdutoJaExiste),
    ],
)
def test_operacao_com_falha_faz_rollback_sem_commit_e_nao_altera_o_banco(
    servico: ServicoEstoque,
    banco: BancoEmMemoria,
    operacao: Callable[[ServicoEstoque], object],
    erro: type[Exception],
) -> None:
    antes = saldos(persistido(banco))

    with pytest.raises(erro):
        operacao(servico)

    assert (banco.commits, banco.rollbacks) == (0, 1)
    assert saldos(persistido(banco)) == antes


def test_falha_no_meio_da_operacao_nao_deixa_alteracao_parcial(
    servico: ServicoEstoque, banco: BancoEmMemoria
) -> None:
    """A mudança feita na cópia da transação não pode vazar sem commit."""
    with pytest.raises(EstoqueInsuficiente):
        servico.reservar("P001", 101, "Reserva X")

    assert persistido(banco).reservas == []


# --- retry de concorrência ------------------------------------------------


def test_conflito_de_versao_e_repetido_ate_dar_certo(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    banco.conflitos_pendentes = MAX_TENTATIVAS - 1

    reserva = servico.reservar("P001", 10, "Reserva 001")

    assert banco.transacoes == MAX_TENTATIVAS
    assert (banco.commits, banco.rollbacks) == (1, MAX_TENTATIVAS - 1)
    assert [r.id for r in persistido(banco).reservas] == [reserva.id]


def test_conflito_de_versao_persistente_levanta_conflito_de_concorrencia_apos_3_tentativas(
    servico: ServicoEstoque, banco: BancoEmMemoria
) -> None:
    banco.conflitos_pendentes = MAX_TENTATIVAS

    with pytest.raises(ConflitoDeConcorrencia):
        servico.reservar("P001", 10, "Reserva 001")

    assert MAX_TENTATIVAS == 3
    assert banco.transacoes == 3
    assert (banco.commits, banco.rollbacks) == (0, 3)
    assert saldos(persistido(banco)) == (100, 100, 0, 0)


def preparar_operacao_com_retry(servico: ServicoEstoque, operacao: str) -> Callable[[], object]:
    """Cria o que a operação precisa (reserva/bloqueio) e devolve a chamada a ser testada."""
    match operacao:
        case "liberar_reserva":
            reserva = servico.reservar("P001", 1, "Reserva X")
            return lambda: servico.liberar_reserva(reserva.id)
        case "liberar_bloqueio":
            bloqueio = servico.bloquear("P001", 1)
            return lambda: servico.liberar_bloqueio(bloqueio.id)
        case _:
            return lambda: OPERACOES_DE_ESCRITA[operacao](servico)


@pytest.mark.parametrize(
    "operacao", ["entrada", "saida", "reservar", "bloquear", "liberar_reserva", "liberar_bloqueio"]
)
def test_todas_as_operacoes_que_alteram_o_produto_tem_retry(
    servico: ServicoEstoque, banco: BancoEmMemoria, operacao: str
) -> None:
    executar = preparar_operacao_com_retry(servico, operacao)
    transacoes_do_preparo = banco.transacoes
    banco.conflitos_pendentes = 1

    executar()

    assert banco.transacoes - transacoes_do_preparo == 2
    assert banco.rollbacks == 1


def test_retry_reavalia_a_regra_com_o_estado_atual(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    """Outra transação consome o estoque antes do commit; a nova tentativa vê isso e falha."""
    banco.escrita_concorrente = lambda b: b.produtos["P001"].reservar(95, "Reserva CONCORRENTE")

    with pytest.raises(EstoqueInsuficiente):
        servico.reservar("P001", 10, "Reserva 001")

    assert banco.transacoes == 2
    assert saldos(persistido(banco)) == (100, 5, 95, 0)


def test_erro_de_dominio_nao_e_repetido(servico: ServicoEstoque, banco: BancoEmMemoria) -> None:
    with pytest.raises(EstoqueInsuficiente):
        servico.saida("P001", 101)

    assert banco.transacoes == 1
