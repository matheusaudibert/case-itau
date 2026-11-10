import logging
import re
from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from estoque.api.schemas import ErroSaida
from estoque.domain.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    ErroDominio,
    EstoqueInsuficiente,
    IdProdutoInvalido,
    NomeProdutoInvalido,
    ProdutoJaExiste,
    ProdutoNaoEncontrado,
    QuantidadeInvalida,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)

logger = logging.getLogger(__name__)

STATUS_POR_ERRO: dict[type[ErroDominio], int] = {
    ProdutoNaoEncontrado: status.HTTP_404_NOT_FOUND,
    ReservaNaoEncontrada: status.HTTP_404_NOT_FOUND,
    BloqueioNaoEncontrado: status.HTTP_404_NOT_FOUND,
    EstoqueInsuficiente: status.HTTP_409_CONFLICT,
    ReservaJaLiberada: status.HTTP_409_CONFLICT,
    BloqueioJaLiberado: status.HTTP_409_CONFLICT,
    ProdutoJaExiste: status.HTTP_409_CONFLICT,
    QuantidadeInvalida: status.HTTP_422_UNPROCESSABLE_CONTENT,
    IdProdutoInvalido: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NomeProdutoInvalido: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


CODIGO_VALIDACAO = "VALIDACAO"

EXEMPLO_POR_ERRO: dict[type[ErroDominio], ErroDominio] = {
    ProdutoNaoEncontrado: ProdutoNaoEncontrado("P999"),
    ReservaNaoEncontrada: ReservaNaoEncontrada(UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    BloqueioNaoEncontrado: BloqueioNaoEncontrado(UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    EstoqueInsuficiente: EstoqueInsuficiente(solicitado=100, disponivel=77),
    ReservaJaLiberada: ReservaJaLiberada(UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    BloqueioJaLiberado: BloqueioJaLiberado(UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")),
    ProdutoJaExiste: ProdutoJaExiste("P001"),
    QuantidadeInvalida: QuantidadeInvalida(0),
    IdProdutoInvalido: IdProdutoInvalido("P١٢٣"),
    NomeProdutoInvalido: NomeProdutoInvalido(),
}

MENSAGEM_POR_CAMPO = {
    "id": 'O id deve seguir o formato "P000": letra P maiúscula seguida de 3 dígitos (ex.: P001).',
    "nome": "O nome é obrigatório e deve ter no máximo 200 caracteres.",
    "quantidade": "A quantidade deve ser um número inteiro maior que zero.",
    "motivo": "O motivo deve ser um texto de no máximo 200 caracteres.",
    "status": "O status deve ser ATIVO ou LIBERADO.",
    "reserva_id": "O id da reserva deve ser um UUID válido.",
    "bloqueio_id": "O id do bloqueio deve ser um UUID válido.",
}

MENSAGEM_POR_STATUS_HTTP = {
    status.HTTP_404_NOT_FOUND: "Rota não encontrada.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Método não permitido nesta rota.",
}

MENSAGEM_CORPO_INVALIDO = "O corpo da requisição deve ser um JSON válido com os campos esperados."

DESCRICAO_POR_STATUS = {
    status.HTTP_404_NOT_FOUND: "Recurso não encontrado",
    status.HTTP_409_CONFLICT: "Conflito com o estado atual do estoque",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Dados inválidos",
}


def codigo_do_erro(erro: type[ErroDominio]) -> str:
    """`EstoqueInsuficiente` -> `ESTOQUE_INSUFICIENTE`."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", erro.__name__).upper()


def documentar_erros(*erros: type[ErroDominio], validacao: str | None = None) -> dict[int | str, dict[str, Any]]:
    """Monta o `responses` do OpenAPI só com os erros que a rota pode devolver.

    Cada status ganha um exemplo por código de erro, com a mesma mensagem que
    a exceção produz em tempo de execução. `validacao` é o campo cujo erro de
    validação serve de exemplo para o código `VALIDACAO`.
    """
    exemplos_por_status: dict[int, dict[str, Any]] = {}
    for erro in erros:
        codigo = codigo_do_erro(erro)
        exemplos_por_status.setdefault(STATUS_POR_ERRO[erro], {})[codigo] = {
            "summary": codigo,
            "value": {"erro": codigo, "mensagem": EXEMPLO_POR_ERRO[erro].mensagem},
        }
    if validacao is not None:
        exemplos_por_status.setdefault(status.HTTP_422_UNPROCESSABLE_CONTENT, {})[CODIGO_VALIDACAO] = {
            "summary": CODIGO_VALIDACAO,
            "value": {"erro": CODIGO_VALIDACAO, "mensagem": MENSAGEM_POR_CAMPO[validacao]},
        }

    return {
        status_code: {
            "model": ErroSaida,
            "description": DESCRICAO_POR_STATUS[status_code],
            "content": {"application/json": {"examples": exemplos}},
        }
        for status_code, exemplos in sorted(exemplos_por_status.items())
    }



def registrar_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ErroDominio, erro_dominio)
    app.add_exception_handler(RequestValidationError, erro_validacao)
    app.add_exception_handler(StarletteHTTPException, erro_http)
    app.add_exception_handler(Exception, erro_inesperado)


def resposta(status_code: int, erro: str, mensagem: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"erro": erro, "mensagem": mensagem})


async def erro_dominio(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ErroDominio)
    status_code = STATUS_POR_ERRO.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return resposta(status_code, codigo_do_erro(type(exc)), exc.mensagem)


async def erro_validacao(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    mensagens = dict.fromkeys(descrever_erro_validacao(e) for e in exc.errors())
    return resposta(status.HTTP_422_UNPROCESSABLE_CONTENT, CODIGO_VALIDACAO, " ".join(mensagens))


def descrever_erro_validacao(erro: dict[str, Any]) -> str:
    """Traduz um erro do Pydantic numa frase simples sobre o campo, sem detalhes técnicos."""
    local = erro.get("loc", ())
    campo = local[1] if len(local) > 1 and isinstance(local[1], str) else None  # sem "body"/"path"/"query"
    if campo is None or erro.get("type") == "json_invalid":
        return MENSAGEM_CORPO_INVALIDO
    if erro.get("type") == "missing":
        return f'O campo "{campo}" é obrigatório.'
    return MENSAGEM_POR_CAMPO.get(campo, f'O campo "{campo}" é inválido.')


async def erro_http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    mensagem = MENSAGEM_POR_STATUS_HTTP.get(exc.status_code, str(exc.detail))
    return resposta(exc.status_code, f"HTTP_{exc.status_code}", mensagem)


async def erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro inesperado", exc_info=exc)
    return resposta(status.HTTP_500_INTERNAL_SERVER_ERROR, "ERRO_INTERNO", "Erro interno inesperado.")


def usar_somente_erros_documentados(app: FastAPI) -> None:
    """Remove do OpenAPI os 422 que o FastAPI acrescenta sozinho (`HTTPValidationError`).

    Eles descrevem `{"detail": [...]}`, que esta API nunca devolve (o handler de
    validação responde `{"erro", "mensagem"}`), e aparecem até em rotas que não
    têm como dar 422. Os 422 reais são declarados em cada rota com `documentar_erros`.
    """
    gerar_original = app.openapi

    def gerar() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = gerar_original()
        for operacoes in schema.get("paths", {}).values():
            for operacao in operacoes.values():
                resposta_422 = operacao.get("responses", {}).get("422", {})
                referencia = resposta_422.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "")
                if referencia.endswith("/HTTPValidationError"):
                    del operacao["responses"]["422"]
        componentes = schema.get("components", {}).get("schemas", {})
        componentes.pop("HTTPValidationError", None)
        componentes.pop("ValidationError", None)
        app.openapi_schema = schema
        return schema

    app.openapi = gerar  # type: ignore[method-assign]
