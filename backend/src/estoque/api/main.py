from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from estoque.api.errors import registrar_handlers, usar_somente_erros_documentados
from estoque.api.routes import router
from estoque.application.services import ServicoEstoque
from estoque.config import Config, carregar_config
from estoque.infra.database import criar_engine, criar_fabrica_sessoes, criar_tabelas
from estoque.infra.seed import popular_banco
from estoque.infra.uow import SqlAlchemyUnitOfWork


def criar_app(config: Config | None = None) -> FastAPI:
    """Raiz de composição: único ponto da API que conhece a infra."""
    config = config or carregar_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = criar_engine(config.database_url)
        criar_tabelas(engine)
        fabrica_sessoes = criar_fabrica_sessoes(engine)
        app.state.fabrica_uow = lambda: SqlAlchemyUnitOfWork(fabrica_sessoes)
        if config.seed_on_startup:
            popular_banco(ServicoEstoque(app.state.fabrica_uow))
        yield
        engine.dispose()

    app = FastAPI(title="Controle de Estoque", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_handlers(app)
    app.include_router(router)
    usar_somente_erros_documentados(app)
    return app


app = criar_app()
