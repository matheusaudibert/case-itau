import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from estoque.domain.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    EstoqueInsuficiente,
    IdProdutoInvalido,
    NomeProdutoInvalido,
    QuantidadeInvalida,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)

FORMATO_ID_PRODUTO = re.compile(r"P[0-9]{3}")


class Status(StrEnum):
    ATIVO = "ATIVO"
    LIBERADO = "LIBERADO"


def agora() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Reserva:
    produto_id: str
    quantidade: int
    motivo: str | None = None
    id: UUID = field(default_factory=uuid4)
    status: Status = Status.ATIVO
    criado_em: datetime = field(default_factory=agora)
    liberado_em: datetime | None = None

    @property
    def ativa(self) -> bool:
        return self.status is Status.ATIVO

    def liberar(self) -> None:
        if not self.ativa:
            raise ReservaJaLiberada(self.id)
        self.status = Status.LIBERADO
        self.liberado_em = agora()


@dataclass
class Bloqueio:
    produto_id: str
    quantidade: int
    motivo: str | None = None
    id: UUID = field(default_factory=uuid4)
    status: Status = Status.ATIVO
    criado_em: datetime = field(default_factory=agora)
    liberado_em: datetime | None = None

    @property
    def ativo(self) -> bool:
        return self.status is Status.ATIVO

    def liberar(self) -> None:
        if not self.ativo:
            raise BloqueioJaLiberado(self.id)
        self.status = Status.LIBERADO
        self.liberado_em = agora()


class Produto:
    """Raiz do agregado de estoque.

    Apenas `total` é estado próprio; reservado, bloqueado e disponível são
    sempre derivados das reservas e bloqueios ativos, de modo que
    `total = disponivel + reservado + bloqueado` vale por construção.
    """

    def __init__(
        self,
        id: str,
        nome: str,
        total: int = 0,
        reservas: list[Reserva] | None = None,
        bloqueios: list[Bloqueio] | None = None,
    ) -> None:
        self.id = validar_id(id)
        self.nome = validar_nome(nome)
        self.total = total
        self.reservas_por_id = {r.id: r for r in reservas or []}
        self.bloqueios_por_id = {b.id: b for b in bloqueios or []}

    @property
    def reservas(self) -> list[Reserva]:
        return list(self.reservas_por_id.values())

    @property
    def bloqueios(self) -> list[Bloqueio]:
        return list(self.bloqueios_por_id.values())

    @property
    def reservado(self) -> int:
        return sum(r.quantidade for r in self.reservas_por_id.values() if r.ativa)

    @property
    def bloqueado(self) -> int:
        return sum(b.quantidade for b in self.bloqueios_por_id.values() if b.ativo)

    @property
    def disponivel(self) -> int:
        return self.total - self.reservado - self.bloqueado

    def entrada(self, qtd: int) -> None:
        validar_quantidade(qtd)
        self.total += qtd

    def saida(self, qtd: int) -> None:
        self.exigir_disponivel(qtd)
        self.total -= qtd

    def reservar(self, qtd: int, motivo: str | None = None) -> Reserva:
        self.exigir_disponivel(qtd)
        reserva = Reserva(produto_id=self.id, quantidade=qtd, motivo=motivo)
        self.reservas_por_id[reserva.id] = reserva
        return reserva

    def bloquear(self, qtd: int, motivo: str | None = None) -> Bloqueio:
        self.exigir_disponivel(qtd)
        bloqueio = Bloqueio(produto_id=self.id, quantidade=qtd, motivo=motivo)
        self.bloqueios_por_id[bloqueio.id] = bloqueio
        return bloqueio

    def liberar_reserva(self, reserva_id: UUID) -> Reserva:
        reserva = self.reservas_por_id.get(reserva_id)
        if reserva is None:
            raise ReservaNaoEncontrada(reserva_id)
        reserva.liberar()
        return reserva

    def liberar_bloqueio(self, bloqueio_id: UUID) -> Bloqueio:
        bloqueio = self.bloqueios_por_id.get(bloqueio_id)
        if bloqueio is None:
            raise BloqueioNaoEncontrado(bloqueio_id)
        bloqueio.liberar()
        return bloqueio

    def exigir_disponivel(self, qtd: int) -> None:
        validar_quantidade(qtd)
        if qtd > self.disponivel:
            raise EstoqueInsuficiente(solicitado=qtd, disponivel=self.disponivel)


def validar_quantidade(qtd: object) -> None:
    """Aceita apenas `int` de fato: `bool` (subclasse de int) e `float` como 5.0 são rejeitados."""
    if type(qtd) is not int or qtd <= 0:
        raise QuantidadeInvalida(qtd)


def validar_id(produto_id: object) -> str:
    """`fullmatch` com [0-9] evita aceitar "P001\\n" (`$`) e dígitos não ASCII (`\\d`)."""
    if not isinstance(produto_id, str) or not FORMATO_ID_PRODUTO.fullmatch(produto_id):
        raise IdProdutoInvalido(produto_id)
    return produto_id


def validar_nome(nome: object) -> str:
    if not isinstance(nome, str) or not nome.strip():
        raise NomeProdutoInvalido()
    return nome.strip()
