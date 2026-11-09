from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from estoque.api.main import criar_app
from estoque.api.routes import obter_fabrica_uow
from estoque.application.services import ServicoEstoque
from estoque.config import Config
from estoque.infra.database import criar_engine, criar_fabrica_sessoes, criar_tabelas
from estoque.infra.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'estoque.db'}"


@pytest.fixture
def engine(database_url: str) -> Iterator[Engine]:
    engine = criar_engine(database_url)
    criar_tabelas(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def fabrica_sessoes(engine: Engine) -> sessionmaker[Session]:
    return criar_fabrica_sessoes(engine)


@pytest.fixture
def nova_uow(fabrica_sessoes: sessionmaker[Session]) -> Callable[[], SqlAlchemyUnitOfWork]:
    return lambda: SqlAlchemyUnitOfWork(fabrica_sessoes)


@pytest.fixture
def servico(nova_uow: Callable[[], SqlAlchemyUnitOfWork]) -> ServicoEstoque:
    return ServicoEstoque(nova_uow)


@pytest.fixture
def cliente(database_url: str, nova_uow: Callable[[], SqlAlchemyUnitOfWork]) -> Iterator[TestClient]:
    """App apontando para o banco temporário, com o Unit of Work injetado pela fixture."""
    app = criar_app(Config(database_url=database_url, cors_origins=["http://localhost:4200"], seed_on_startup=False))
    app.dependency_overrides[obter_fabrica_uow] = lambda: nova_uow
    with TestClient(app) as cliente:
        yield cliente
