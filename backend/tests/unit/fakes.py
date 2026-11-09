import copy
from collections.abc import Callable
from types import TracebackType
from typing import Self
from uuid import UUID

from estoque.application.ports import ConflitoDeVersao
from estoque.domain.produto import Bloqueio, Produto, Reserva


class BancoEmMemoria:
    """Estado "persistido", compartilhado entre as unidades de trabalho.

    `conflitos_pendentes` faz os próximos N commits falharem com
    `ConflitoDeVersao`, simulando outra transação gravando antes.
    `escrita_concorrente`, se definida, roda uma vez no próximo commit
    (alterando o banco) e o faz falhar com `ConflitoDeVersao`.
    """

    def __init__(self) -> None:
        self.produtos: dict[str, Produto] = {}
        self.conflitos_pendentes = 0
        self.escrita_concorrente: Callable[[BancoEmMemoria], None] | None = None
        self.transacoes = 0
        self.commits = 0
        self.rollbacks = 0

    def inserir(self, produto: Produto) -> None:
        self.produtos[produto.id] = copy.deepcopy(produto)


class RepositorioEmMemoria:
    def __init__(self, produtos: dict[str, Produto]) -> None:
        self.produtos = produtos

    def obter(self, produto_id: str) -> Produto | None:
        return self.produtos.get(produto_id)

    def listar(self) -> list[Produto]:
        return sorted(self.produtos.values(), key=lambda p: p.id)

    def adicionar(self, produto: Produto) -> None:
        self.produtos[produto.id] = produto

    def salvar(self, produto: Produto) -> None:
        self.produtos[produto.id] = produto

    def obter_reserva(self, reserva_id: UUID) -> Reserva | None:
        return next(
            (r for p in self.produtos.values() for r in p.reservas if r.id == reserva_id),
            None,
        )

    def obter_bloqueio(self, bloqueio_id: UUID) -> Bloqueio | None:
        return next(
            (b for p in self.produtos.values() for b in p.bloqueios if b.id == bloqueio_id),
            None,
        )


class UnitOfWorkEmMemoria:
    """Trabalha sobre uma cópia do banco; só o commit a torna visível."""

    def __init__(self, banco: BancoEmMemoria) -> None:
        self.banco = banco
        self.produtos = RepositorioEmMemoria({})

    def __enter__(self) -> Self:
        self.banco.transacoes += 1
        self.produtos = RepositorioEmMemoria(copy.deepcopy(self.banco.produtos))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        if self.banco.escrita_concorrente is not None:
            escrita, self.banco.escrita_concorrente = self.banco.escrita_concorrente, None
            escrita(self.banco)
            raise ConflitoDeVersao()
        if self.banco.conflitos_pendentes > 0:
            self.banco.conflitos_pendentes -= 1
            raise ConflitoDeVersao()
        self.banco.produtos = copy.deepcopy(self.produtos.produtos)
        self.banco.commits += 1

    def rollback(self) -> None:
        self.banco.rollbacks += 1
