"""O OpenAPI (Swagger) descreve exatamente as respostas que a API devolve.

Para cada rota: todo erro documentado é provocado de verdade e responde com o
status e o código anunciados, e nenhum erro provocável fica sem documentação.
"""

from collections.abc import Callable, Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from estoque.api.main import criar_app
from estoque.api.routes import obter_fabrica_uow
from estoque.application.ports import ConflitoDeVersao
from estoque.application.services import ServicoEstoque
from estoque.config import Config
from estoque.infra.uow import SqlAlchemyUnitOfWork

UUID_INEXISTENTE = str(uuid4())

# (método, rota no OpenAPI, status, código, rota chamada, corpo)
CASOS_DE_ERRO: list[tuple[str, str, int, str, str, dict[str, Any] | None]] = [
    ("post", "/produtos", 409, "PRODUTO_JA_EXISTE", "/produtos", {"id": "P001", "nome": "Outro"}),
    ("post", "/produtos", 422, "ID_PRODUTO_INVALIDO", "/produtos", {"id": "P١٢٣", "nome": "X"}),
    ("post", "/produtos", 422, "NOME_PRODUTO_INVALIDO", "/produtos", {"id": "P002", "nome": "   "}),
    ("post", "/produtos", 422, "VALIDACAO", "/produtos", {"id": "p001", "nome": "X"}),
    ("get", "/produtos/{produto_id}", 404, "PRODUTO_NAO_ENCONTRADO", "/produtos/P999", None),
    ("post", "/produtos/{produto_id}/entradas", 404, "PRODUTO_NAO_ENCONTRADO", "/produtos/P999/entradas", {"quantidade": 1}),
    ("post", "/produtos/{produto_id}/entradas", 422, "VALIDACAO", "/produtos/P001/entradas", {"quantidade": 0}),
    ("post", "/produtos/{produto_id}/saidas", 404, "PRODUTO_NAO_ENCONTRADO", "/produtos/P999/saidas", {"quantidade": 1}),
    ("post", "/produtos/{produto_id}/saidas", 409, "ESTOQUE_INSUFICIENTE", "/produtos/P001/saidas", {"quantidade": 1000}),
    ("post", "/produtos/{produto_id}/saidas", 422, "VALIDACAO", "/produtos/P001/saidas", {"quantidade": -1}),
    ("post", "/produtos/{produto_id}/reservas", 404, "PRODUTO_NAO_ENCONTRADO", "/produtos/P999/reservas", {"quantidade": 1, "motivo": "Reserva"}),
    ("post", "/produtos/{produto_id}/reservas", 409, "ESTOQUE_INSUFICIENTE", "/produtos/P001/reservas", {"quantidade": 1000, "motivo": "Reserva"}),
    ("post", "/produtos/{produto_id}/reservas", 422, "VALIDACAO", "/produtos/P001/reservas", {"quantidade": 0}),
    ("get", "/produtos/{produto_id}/reservas", 404, "PRODUTO_NAO_ENCONTRADO", "/produtos/P999/reservas", None),
    ("get", "/produtos/{produto_id}/reservas", 422, "VALIDACAO", "/produtos/P001/reservas?status=X", None),
    ("get", "/reservas/{reserva_id}", 404, "RESERVA_NAO_ENCONTRADA", f"/reservas/{UUID_INEXISTENTE}", None),
    ("get", "/reservas/{reserva_id}", 422, "VALIDACAO", "/reservas/abc", None),
    ("post", "/reservas/{reserva_id}/liberar", 404, "RESERVA_NAO_ENCONTRADA", f"/reservas/{UUID_INEXISTENTE}/liberar", None),
    ("post", "/reservas/{reserva_id}/liberar", 409, "RESERVA_JA_LIBERADA", "/reservas/{reserva_liberada}/liberar", None),
    ("post", "/reservas/{reserva_id}/liberar", 422, "VALIDACAO", "/reservas/abc/liberar", None),
    ("post", "/produtos/{produto_id}/bloqueios", 404, "PRODUTO_NAO_ENCONTRADO", "/produtos/P999/bloqueios", {"quantidade": 1}),
    ("post", "/produtos/{produto_id}/bloqueios", 409, "ESTOQUE_INSUFICIENTE", "/produtos/P001/bloqueios", {"quantidade": 1000}),
    ("post", "/produtos/{produto_id}/bloqueios", 422, "VALIDACAO", "/produtos/P001/bloqueios", {"quantidade": "1"}),
    ("get", "/produtos/{produto_id}/bloqueios", 404, "PRODUTO_NAO_ENCONTRADO", "/produtos/P999/bloqueios", None),
    ("get", "/produtos/{produto_id}/bloqueios", 422, "VALIDACAO", "/produtos/P001/bloqueios?status=X", None),
    ("get", "/bloqueios/{bloqueio_id}", 404, "BLOQUEIO_NAO_ENCONTRADO", f"/bloqueios/{UUID_INEXISTENTE}", None),
    ("get", "/bloqueios/{bloqueio_id}", 422, "VALIDACAO", "/bloqueios/abc", None),
    ("post", "/bloqueios/{bloqueio_id}/liberar", 404, "BLOQUEIO_NAO_ENCONTRADO", f"/bloqueios/{UUID_INEXISTENTE}/liberar", None),
    ("post", "/bloqueios/{bloqueio_id}/liberar", 409, "BLOQUEIO_JA_LIBERADO", "/bloqueios/{bloqueio_liberado}/liberar", None),
    ("post", "/bloqueios/{bloqueio_id}/liberar", 422, "VALIDACAO", "/bloqueios/abc/liberar", None),
]

# Rotas que gravam com retry: provocadas com um Unit of Work cujo commit sempre conflita.
CASOS_DE_CONFLITO: list[tuple[str, str, str, dict[str, Any] | None]] = [
    ("post", "/produtos/{produto_id}/entradas", "/produtos/P001/entradas", {"quantidade": 1}),
    ("post", "/produtos/{produto_id}/saidas", "/produtos/P001/saidas", {"quantidade": 1}),
    ("post", "/produtos/{produto_id}/reservas", "/produtos/P001/reservas", {"quantidade": 1, "motivo": "Reserva"}),
    ("post", "/produtos/{produto_id}/bloqueios", "/produtos/P001/bloqueios", {"quantidade": 1}),
    ("post", "/reservas/{reserva_id}/liberar", "/reservas/{reserva_ativa}/liberar", None),
    ("post", "/bloqueios/{bloqueio_id}/liberar", "/bloqueios/{bloqueio_ativo}/liberar", None),
]


class UnitOfWorkSempreEmConflito(SqlAlchemyUnitOfWork):
    def commit(self) -> None:
        raise ConflitoDeVersao()


@pytest.fixture
def ids(servico: ServicoEstoque) -> dict[str, str]:
    """P001 com estoque, uma reserva e um bloqueio ativos e outros dois já liberados."""
    servico.criar_produto("P001", "Teclado")
    servico.entrada("P001", 100)
    reserva_liberada = servico.reservar("P001", 1, "Reserva L")
    servico.liberar_reserva(reserva_liberada.id)
    bloqueio_liberado = servico.bloquear("P001", 1)
    servico.liberar_bloqueio(bloqueio_liberado.id)
    return {
        "reserva_ativa": str(servico.reservar("P001", 1, "Reserva A").id),
        "bloqueio_ativo": str(servico.bloquear("P001", 1).id),
        "reserva_liberada": str(reserva_liberada.id),
        "bloqueio_liberado": str(bloqueio_liberado.id),
    }


@pytest.fixture
def openapi(cliente: TestClient) -> dict[str, Any]:
    return cliente.get("/openapi.json").json()


@pytest.fixture
def cliente_em_conflito(database_url: str, fabrica_sessoes: Any) -> Iterator[TestClient]:
    app = criar_app(Config(database_url=database_url, cors_origins=[], seed_on_startup=False))
    fabrica: Callable[[], SqlAlchemyUnitOfWork] = lambda: UnitOfWorkSempreEmConflito(fabrica_sessoes)
    app.dependency_overrides[obter_fabrica_uow] = lambda: fabrica
    with TestClient(app) as cliente:
        yield cliente


def erros_documentados(openapi: dict[str, Any]) -> set[tuple[str, str, int, str]]:
    documentados = set()
    for rota, operacoes in openapi["paths"].items():
        for metodo, operacao in operacoes.items():
            for status_code, resposta in operacao["responses"].items():
                if status_code.startswith("2"):
                    continue
                exemplos = resposta.get("content", {}).get("application/json", {}).get("examples")
                assert exemplos, f"{metodo.upper()} {rota} {status_code} sem exemplo"
                for codigo, exemplo in exemplos.items():
                    assert exemplo["value"]["erro"] == codigo
                    assert set(exemplo["value"]) == {"erro", "mensagem"}
                    documentados.add((metodo, rota, int(status_code), codigo))
    return documentados


def test_cada_erro_documentado_tem_um_caso_que_o_provoca_e_vice_versa(openapi: dict[str, Any]) -> None:
    provocados = {(m, r, s, c) for m, r, s, c, chamada, corpo in CASOS_DE_ERRO}
    provocados |= {(m, r, 409, "CONFLITO_DE_CONCORRENCIA") for m, r, chamada, corpo in CASOS_DE_CONFLITO}

    assert erros_documentados(openapi) == provocados


def test_openapi_nao_documenta_o_formato_de_erro_padrao_do_fastapi(openapi: dict[str, Any]) -> None:
    assert "HTTPValidationError" not in openapi["components"]["schemas"]
    assert "422" not in openapi["paths"]["/produtos/{produto_id}"]["get"]["responses"]
    assert set(openapi["paths"]["/produtos"]["get"]["responses"]) == {"200"}


@pytest.mark.parametrize(
    ("metodo", "rota_doc", "status_code", "codigo", "rota", "corpo"),
    CASOS_DE_ERRO,
    ids=[f"{m.upper()} {r} {s} {c}" for m, r, s, c, chamada, corpo in CASOS_DE_ERRO],
)
def test_erro_documentado_e_o_que_a_api_devolve(
    cliente: TestClient,
    openapi: dict[str, Any],
    ids: dict[str, str],
    metodo: str,
    rota_doc: str,
    status_code: int,
    codigo: str,
    rota: str,
    corpo: dict[str, Any] | None,
) -> None:
    resposta = cliente.request(metodo, rota.format(**ids), json=corpo)

    assert resposta.status_code == status_code
    assert resposta.json()["erro"] == codigo
    exemplo = openapi["paths"][rota_doc][metodo]["responses"][str(status_code)]["content"]["application/json"]
    assert codigo in exemplo["examples"]


@pytest.mark.parametrize(("metodo", "rota_doc", "rota", "corpo"), CASOS_DE_CONFLITO, ids=[c[1] for c in CASOS_DE_CONFLITO])
def test_conflito_de_concorrencia_documentado_e_o_que_a_api_devolve(
    cliente_em_conflito: TestClient,
    ids: dict[str, str],
    metodo: str,
    rota_doc: str,
    rota: str,
    corpo: dict[str, Any] | None,
) -> None:
    resposta = cliente_em_conflito.request(metodo, rota.format(**ids), json=corpo)

    assert resposta.status_code == 409
    assert resposta.json() == {
        "erro": "CONFLITO_DE_CONCORRENCIA",
        "mensagem": "O produto foi alterado por outra operação ao mesmo tempo. Tente novamente.",
    }


def test_mensagens_dos_exemplos_sao_as_mesmas_da_api(cliente: TestClient, openapi: dict[str, Any], ids: dict[str, str]) -> None:
    """Onde a mensagem não depende de id gerado, o exemplo é idêntico à resposta real."""
    def exemplo(rota: str, metodo: str, status_code: int, codigo: str) -> dict[str, str]:
        return openapi["paths"][rota][metodo]["responses"][str(status_code)]["content"]["application/json"]["examples"][codigo]["value"]

    assert cliente.get("/produtos/P999").json() == exemplo("/produtos/{produto_id}", "get", 404, "PRODUTO_NAO_ENCONTRADO")
    assert cliente.post("/produtos", json={"id": "P001", "nome": "X"}).json() == exemplo(
        "/produtos", "post", 409, "PRODUTO_JA_EXISTE"
    )
    assert cliente.post("/produtos", json={"id": "P002", "nome": " "}).json() == exemplo(
        "/produtos", "post", 422, "NOME_PRODUTO_INVALIDO"
    )
    assert cliente.post("/produtos/P001/entradas", json={"quantidade": 0}).json() == exemplo(
        "/produtos/{produto_id}/entradas", "post", 422, "VALIDACAO"
    )


def campos_do_schema(openapi: dict[str, Any], rota: str, metodo: str) -> set[str]:
    sucesso = next(v for k, v in openapi["paths"][rota][metodo]["responses"].items() if k.startswith("2"))
    schema = sucesso["content"]["application/json"]["schema"]
    referencia = schema.get("items", schema)["$ref"]
    return set(openapi["components"]["schemas"][referencia.rsplit("/", 1)[-1]]["properties"])


def test_respostas_de_sucesso_tem_os_campos_documentados(
    cliente: TestClient, openapi: dict[str, Any], ids: dict[str, str]
) -> None:
    chamadas = [
        ("post", "/produtos", "/produtos", {"id": "P002", "nome": "Mouse"}, 201),
        ("get", "/produtos", "/produtos", None, 200),
        ("get", "/produtos/{produto_id}", "/produtos/P001", None, 200),
        ("post", "/produtos/{produto_id}/entradas", "/produtos/P001/entradas", {"quantidade": 1}, 200),
        ("post", "/produtos/{produto_id}/saidas", "/produtos/P001/saidas", {"quantidade": 1}, 200),
        ("post", "/produtos/{produto_id}/reservas", "/produtos/P001/reservas", {"quantidade": 1, "motivo": "P"}, 201),
        ("get", "/produtos/{produto_id}/reservas", "/produtos/P001/reservas", None, 200),
        ("get", "/reservas/{reserva_id}", f"/reservas/{ids['reserva_ativa']}", None, 200),
        ("post", "/reservas/{reserva_id}/liberar", f"/reservas/{ids['reserva_ativa']}/liberar", None, 200),
        ("post", "/produtos/{produto_id}/bloqueios", "/produtos/P001/bloqueios", {"quantidade": 1}, 201),
        ("get", "/produtos/{produto_id}/bloqueios", "/produtos/P001/bloqueios", None, 200),
        ("get", "/bloqueios/{bloqueio_id}", f"/bloqueios/{ids['bloqueio_ativo']}", None, 200),
        ("post", "/bloqueios/{bloqueio_id}/liberar", f"/bloqueios/{ids['bloqueio_ativo']}/liberar", None, 200),
    ]
    rotas_documentadas = {(m, r) for r, ops in openapi["paths"].items() for m in ops}
    assert {(m, r) for m, r, chamada, corpo, status in chamadas} == rotas_documentadas

    for metodo, rota_doc, rota, corpo, status_code in chamadas:
        resposta = cliente.request(metodo, rota, json=corpo)
        assert resposta.status_code == status_code, rota
        assert str(status_code) in openapi["paths"][rota_doc][metodo]["responses"], rota
        corpo_resposta = resposta.json()
        item = corpo_resposta[0] if isinstance(corpo_resposta, list) else corpo_resposta
        assert set(item) == campos_do_schema(openapi, rota_doc, metodo), rota
