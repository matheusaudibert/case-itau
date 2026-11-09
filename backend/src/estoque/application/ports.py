from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from estoque.domain.produto import Bloqueio, Produto, Reserva


class ConflitoDeVersao(Exception):
    """Outra transação alterou o produto entre a leitura e o commit.

    A infra traduz o erro de lock otimista do banco para esta exceção;
    os casos de uso a tratam com nova tentativa.
    """


class RepositorioProdutos(Protocol):
    def obter(self, produto_id: str) -> Produto | None: ...

    def listar(self) -> list[Produto]: ...

    def adicionar(self, produto: Produto) -> None: ...

    def salvar(self, produto: Produto) -> None: ...

    def obter_reserva(self, reserva_id: UUID) -> Reserva | None: ...

    def obter_bloqueio(self, bloqueio_id: UUID) -> Bloqueio | None: ...


class UnitOfWork(Protocol):
    """Uma transação. Ao sair do `with` com exceção, faz rollback.

    Sem `commit()` explícito nada é persistido. `commit()` pode levantar
    `ConflitoDeVersao`.
    """

    produtos: RepositorioProdutos

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
