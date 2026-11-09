"""Invariantes do Produto ao longo de sequências de operações.

Após cada passo: `total = disponivel + reservado + bloqueado` e nenhum saldo
negativo. Passos que devem ser recusados levantam o erro esperado e deixam o
estado (saldos, reservas e bloqueios) exatamente como estava.
"""

from dataclasses import dataclass
from itertools import permutations
from uuid import UUID, uuid4

import pytest

from estoque.domain.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    ErroDominio,
    EstoqueInsuficiente,
    QuantidadeInvalida,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)
from estoque.domain.produto import Produto, Status
from tests.unit.saldos import saldos


@dataclass(frozen=True)
class Passo:
    operacao: str
    quantidade: object = None
    rotulo: str | None = None
    motivo: str | None = "Reserva X"
    erro: type[ErroDominio] | None = None

    def __str__(self) -> str:
        alvo = self.rotulo if self.quantidade is None else repr(self.quantidade)
        return f"{self.operacao}({alvo})" + (f" -> {self.erro.__name__}" if self.erro else "")


def entrada(qtd: object, erro: type[ErroDominio] | None = None) -> Passo:
    return Passo("entrada", qtd, erro=erro)


def saida(qtd: object, erro: type[ErroDominio] | None = None) -> Passo:
    return Passo("saida", qtd, erro=erro)


def reservar(
    qtd: object,
    rotulo: str | None = None,
    erro: type[ErroDominio] | None = None,
    motivo: str | None = "Reserva X",
) -> Passo:
    return Passo("reservar", qtd, rotulo, motivo, erro)


def bloquear(qtd: object, rotulo: str | None = None, erro: type[ErroDominio] | None = None) -> Passo:
    return Passo("bloquear", qtd, rotulo, erro=erro)


def liberar_reserva(rotulo: str, erro: type[ErroDominio] | None = None) -> Passo:
    return Passo("liberar_reserva", rotulo=rotulo, erro=erro)


def liberar_bloqueio(rotulo: str, erro: type[ErroDominio] | None = None) -> Passo:
    return Passo("liberar_bloqueio", rotulo=rotulo, erro=erro)


def executar(produto: Produto, passo: Passo, ids: dict[str, UUID]) -> None:
    """Rótulos dão nome às reservas/bloqueios criados; rótulo desconhecido vira um UUID que não existe."""
    match passo.operacao:
        case "entrada":
            produto.entrada(passo.quantidade)  # type: ignore[arg-type]
        case "saida":
            produto.saida(passo.quantidade)  # type: ignore[arg-type]
        case "reservar":
            reserva = produto.reservar(passo.quantidade, passo.motivo)  # type: ignore[arg-type]
            if passo.rotulo:
                ids[passo.rotulo] = reserva.id
        case "bloquear":
            bloqueio = produto.bloquear(passo.quantidade)  # type: ignore[arg-type]
            if passo.rotulo:
                ids[passo.rotulo] = bloqueio.id
        case "liberar_reserva":
            produto.liberar_reserva(ids.get(passo.rotulo or "", uuid4()))
        case "liberar_bloqueio":
            produto.liberar_bloqueio(ids.get(passo.rotulo or "", uuid4()))
        case _:
            raise AssertionError(f"operação desconhecida: {passo.operacao}")


def estado(produto: Produto) -> tuple[object, ...]:
    """Tudo que uma operação pode alterar: saldos e cada reserva/bloqueio com status e data de liberação."""
    return (
        saldos(produto),
        sorted((str(r.id), r.quantidade, r.status, r.liberado_em) for r in produto.reservas),
        sorted((str(b.id), b.quantidade, b.status, b.liberado_em) for b in produto.bloqueios),
    )


def verificar_invariantes(produto: Produto, contexto: str) -> None:
    total, disponivel, reservado, bloqueado = saldos(produto)
    assert total == disponivel + reservado + bloqueado, contexto
    assert min(total, disponivel, reservado, bloqueado) >= 0, contexto
    assert reservado == sum(r.quantidade for r in produto.reservas if r.status is Status.ATIVO), contexto
    assert bloqueado == sum(b.quantidade for b in produto.bloqueios if b.status is Status.ATIVO), contexto


SEQUENCIAS = [
    pytest.param(
        [
            entrada(100),
            reservar(30, "r1"),
            bloquear(20, "b1"),
            saida(50),
            liberar_reserva("r1"),
            liberar_bloqueio("b1"),
            saida(50),
        ],
        (0, 0, 0, 0),
        id="ciclo_completo_ate_zerar",
    ),
    pytest.param(
        [
            entrada(10),
            reservar(10, "r1"),
            saida(1, EstoqueInsuficiente),
            reservar(1, erro=EstoqueInsuficiente),
            bloquear(1, erro=EstoqueInsuficiente),
            liberar_reserva("r1"),
            saida(10),
        ],
        (0, 0, 0, 0),
        id="reservar_tudo_e_tentar_saida",
    ),
    pytest.param(
        [
            entrada(5),
            bloquear(5, "b1"),
            reservar(1, erro=EstoqueInsuficiente),
            saida(1, EstoqueInsuficiente),
            entrada(1),
            reservar(1),
        ],
        (6, 0, 1, 5),
        id="bloquear_tudo_e_tentar_reservar",
    ),
    pytest.param(
        [
            entrada(20),
            reservar(15),
            saida(6, EstoqueInsuficiente),
            saida(5),
            saida(1, EstoqueInsuficiente),
        ],
        (15, 0, 15, 0),
        id="saida_nao_consome_reservas",
    ),
    pytest.param(
        [
            entrada(20),
            bloquear(12),
            reservar(8),
            saida(1, EstoqueInsuficiente),
            saida(20, EstoqueInsuficiente),
        ],
        (20, 0, 8, 12),
        id="saida_nao_consome_bloqueios_nem_reservas",
    ),
    pytest.param(
        [
            entrada(10),
            reservar(4, "r1"),
            liberar_reserva("r1"),
            liberar_reserva("r1", ReservaJaLiberada),
            bloquear(3, "b1"),
            liberar_bloqueio("b1"),
            liberar_bloqueio("b1", BloqueioJaLiberado),
        ],
        (10, 10, 0, 0),
        id="liberar_duas_vezes",
    ),
    pytest.param(
        [
            entrada(10),
            reservar(2, "r1"),
            bloquear(3, "b1"),
            liberar_reserva("fantasma", ReservaNaoEncontrada),
            liberar_bloqueio("fantasma", BloqueioNaoEncontrado),
            liberar_reserva("b1", ReservaNaoEncontrada),
            liberar_bloqueio("r1", BloqueioNaoEncontrado),
        ],
        (10, 5, 2, 3),
        id="liberar_inexistente_ou_do_tipo_errado",
    ),
    pytest.param(
        [
            entrada(0, QuantidadeInvalida),
            entrada(-5, QuantidadeInvalida),
            entrada(2.5, QuantidadeInvalida),
            entrada(True, QuantidadeInvalida),
            entrada(10),
            saida("3", QuantidadeInvalida),
            reservar(0, erro=QuantidadeInvalida),
            reservar(-1, erro=QuantidadeInvalida),
            bloquear(None, erro=QuantidadeInvalida),
            bloquear(1.0, erro=QuantidadeInvalida),
        ],
        (10, 10, 0, 0),
        id="quantidades_invalidas_em_todas_as_operacoes",
    ),
    pytest.param(
        [
            saida(1, EstoqueInsuficiente),
            reservar(1, erro=EstoqueInsuficiente),
            bloquear(1, erro=EstoqueInsuficiente),
        ],
        (0, 0, 0, 0),
        id="produto_sem_estoque",
    ),
    pytest.param(
        [
            entrada(5),
            reservar(1, "r1"),
            reservar(1, "r2"),
            reservar(1, "r3"),
            reservar(1, "r4"),
            reservar(1, "r5"),
            reservar(1, erro=EstoqueInsuficiente),
            liberar_reserva("r3"),
            reservar(1),
            reservar(1, erro=EstoqueInsuficiente),
        ],
        (5, 0, 5, 0),
        id="muitas_reservas_pequenas_ate_o_limite",
    ),
    pytest.param(
        [
            entrada(10),
            bloquear(10, "b1"),
            liberar_bloqueio("b1"),
            reservar(10, "r1"),
            saida(1, EstoqueInsuficiente),
            liberar_reserva("r1"),
            bloquear(10),
        ],
        (10, 0, 0, 10),
        id="quantidade_liberada_volta_a_ser_usavel",
    ),
    pytest.param(
        [
            entrada(10),
            reservar(5, motivo=None),
            reservar(3, motivo=""),
            reservar(3, erro=EstoqueInsuficiente, motivo=None),
        ],
        (10, 2, 8, 0),
        id="reserva_sem_motivo_aceita",
    ),
    pytest.param(
        [
            entrada(50),
            reservar(10, "r1"),
            reservar(10, "r2"),
            bloquear(10, "b1"),
            saida(20),
            saida(1, EstoqueInsuficiente),
            liberar_reserva("r1"),
            bloquear(10, "b2"),
            entrada(5),
            reservar(6, erro=EstoqueInsuficiente),
            reservar(5, "r3"),
            liberar_bloqueio("b1"),
            liberar_reserva("r2"),
            saida(20),
            liberar_reserva("r2", ReservaJaLiberada),
            liberar_bloqueio("b2"),
            saida(11, EstoqueInsuficiente),
            saida(10),
        ],
        (5, 0, 5, 0),
        id="sequencia_longa_mista",
    ),
]


@pytest.mark.parametrize(("passos", "saldos_finais"), SEQUENCIAS)
def test_invariantes_valem_apos_cada_passo_da_sequencia(
    passos: list[Passo], saldos_finais: tuple[int, int, int, int]
) -> None:
    produto = Produto("P001", "Teclado")
    ids: dict[str, UUID] = {}
    verificar_invariantes(produto, "estado inicial")

    for numero, passo in enumerate(passos, start=1):
        contexto = f"passo {numero}: {passo}"
        antes = estado(produto)

        if passo.erro is None:
            executar(produto, passo, ids)
        else:
            with pytest.raises(passo.erro):
                executar(produto, passo, ids)
            assert estado(produto) == antes, f"{contexto} recusado, mas alterou o estado"

        verificar_invariantes(produto, contexto)

    assert saldos(produto) == saldos_finais


# --- todas as ordens de um conjunto de operações --------------------------

OPERACOES_PARA_PERMUTAR = [
    entrada(10),
    saida(7),
    reservar(6, "r1"),
    bloquear(5, "b1"),
    liberar_reserva("r1"),
    liberar_bloqueio("b1"),
]


@dataclass
class Referencia:
    """Contabilidade independente do domínio, usada para prever o resultado de cada passo."""

    total: int = 0
    reservado: int = 0
    bloqueado: int = 0

    @property
    def disponivel(self) -> int:
        return self.total - self.reservado - self.bloqueado


def prever_e_aplicar(ref: Referencia, passo: Passo, ativos: dict[str, int]) -> bool:
    """Devolve se o passo deve ser aceito e, se sim, aplica-o na referência."""
    qtd = passo.quantidade if isinstance(passo.quantidade, int) else 0
    match passo.operacao:
        case "entrada":
            ref.total += qtd
        case "saida" if qtd <= ref.disponivel:
            ref.total -= qtd
        case "reservar" if qtd <= ref.disponivel:
            ref.reservado += qtd
            ativos[passo.rotulo or ""] = qtd
        case "bloquear" if qtd <= ref.disponivel:
            ref.bloqueado += qtd
            ativos[passo.rotulo or ""] = qtd
        case "liberar_reserva" if passo.rotulo in ativos:
            ref.reservado -= ativos.pop(passo.rotulo)
        case "liberar_bloqueio" if passo.rotulo in ativos:
            ref.bloqueado -= ativos.pop(passo.rotulo)
        case _:
            return False
    return True


@pytest.mark.parametrize(
    "ordem",
    list(permutations(OPERACOES_PARA_PERMUTAR)),
    ids=lambda ordem: " > ".join(str(p) for p in ordem),
)
def test_invariantes_valem_em_qualquer_ordem_das_operacoes(ordem: tuple[Passo, ...]) -> None:
    """Cada uma das 720 ordens: o domínio aceita exatamente o que a referência prevê."""
    produto = Produto("P001", "Teclado")
    ids: dict[str, UUID] = {}
    referencia = Referencia()
    ativos: dict[str, int] = {}

    for numero, passo in enumerate(ordem, start=1):
        contexto = f"passo {numero}: {passo}"
        antes = estado(produto)
        deve_aceitar = prever_e_aplicar(referencia, passo, ativos)

        if deve_aceitar:
            executar(produto, passo, ids)
        else:
            with pytest.raises(ErroDominio):
                executar(produto, passo, ids)
            assert estado(produto) == antes, f"{contexto} recusado, mas alterou o estado"

        verificar_invariantes(produto, contexto)
        assert saldos(produto) == (
            referencia.total,
            referencia.disponivel,
            referencia.reservado,
            referencia.bloqueado,
        ), contexto
