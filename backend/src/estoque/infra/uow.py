from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from estoque.application.ports import ConflitoDeVersao
from estoque.infra.repository import RepositorioSqlAlchemy


class SqlAlchemyUnitOfWork:
    """Uma sessão = uma transação. Cada `with` abre uma sessão nova."""

    produtos: RepositorioSqlAlchemy

    def __init__(self, fabrica_sessoes: sessionmaker[Session]) -> None:
        self.fabrica_sessoes = fabrica_sessoes

    def __enter__(self) -> Self:
        self.sessao = self.fabrica_sessoes()
        self.produtos = RepositorioSqlAlchemy(self.sessao)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            self.sessao.close()

    def commit(self) -> None:
        try:
            self.sessao.commit()
        except StaleDataError as erro:
            raise ConflitoDeVersao() from erro

    def rollback(self) -> None:
        self.sessao.rollback()
