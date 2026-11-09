from pathlib import Path
from sqlite3 import Connection as ConexaoSqlite
from typing import Any

from sqlalchemy import Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker

from estoque.infra.models import Base


def criar_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", ativar_foreign_keys)
    return engine


def criar_fabrica_sessoes(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def criar_tabelas(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def ativar_foreign_keys(conexao: ConexaoSqlite, registro: Any) -> None:
    cursor = conexao.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
