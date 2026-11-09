from typing import Any

import pytest
from fastapi.testclient import TestClient

FORMATO_ID = 'O id deve seguir o formato "P000": letra P maiúscula seguida de 3 dígitos (ex.: P001).'
QUANTIDADE = "A quantidade deve ser um número inteiro maior que zero."
CORPO = "O corpo da requisição deve ser um JSON válido com os campos esperados."


@pytest.fixture
def com_produto(cliente: TestClient) -> TestClient:
    assert cliente.post("/produtos", json={"id": "P001", "nome": "Teclado mecânico"}).status_code == 201
    assert cliente.post("/produtos/P001/entradas", json={"quantidade": 10}).status_code == 200
    return cliente


@pytest.mark.parametrize(
    ("metodo", "rota", "corpo", "mensagem"),
    [
        ("post", "/produtos", {"id": "p001", "nome": "X"}, FORMATO_ID),
        ("post", "/produtos", {"id": 1, "nome": "X"}, FORMATO_ID),
        ("post", "/produtos", {"id": "P002", "nome": ""}, "O nome é obrigatório e deve ter no máximo 200 caracteres."),
        ("post", "/produtos", {"id": "P002", "nome": "X" * 201}, "O nome é obrigatório e deve ter no máximo 200 caracteres."),
        ("post", "/produtos", {"nome": "X"}, 'O campo "id" é obrigatório.'),
        ("post", "/produtos", {}, 'O campo "id" é obrigatório. O campo "nome" é obrigatório.'),
        ("post", "/produtos", [1], CORPO),
        ("post", "/produtos", None, CORPO),
        ("post", "/produtos/P001/entradas", {"quantidade": 0}, QUANTIDADE),
        ("post", "/produtos/P001/saidas", {"quantidade": "5"}, QUANTIDADE),
        ("post", "/produtos/P001/reservas", {"quantidade": 1.5}, QUANTIDADE),
        ("post", "/produtos/P001/bloqueios", {}, 'O campo "quantidade" é obrigatório.'),
        ("post", "/produtos/P001/reservas", {"quantidade": 1, "motivo": "X" * 201}, "O motivo deve ser um texto de no máximo 200 caracteres."),
        ("get", "/produtos/P001/reservas?status=X", None, "O status deve ser ATIVO ou LIBERADO."),
        ("get", "/reservas/abc", None, "O id da reserva deve ser um UUID válido."),
        ("post", "/bloqueios/abc/liberar", None, "O id do bloqueio deve ser um UUID válido."),
    ],
)
def test_erro_de_validacao_devolve_mensagem_simples(
    com_produto: TestClient, metodo: str, rota: str, corpo: Any, mensagem: str
) -> None:
    resposta = com_produto.request(metodo, rota, json=corpo)

    assert resposta.status_code == 422
    assert resposta.json() == {"erro": "VALIDACAO", "mensagem": mensagem}


def test_json_malformado_devolve_mensagem_de_corpo_invalido(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos", content="{x", headers={"Content-Type": "application/json"})

    assert resposta.status_code == 422
    assert resposta.json() == {"erro": "VALIDACAO", "mensagem": CORPO}


@pytest.mark.parametrize(
    ("metodo", "rota", "corpo", "status_code", "mensagem"),
    [
        ("post", "/produtos", {"id": "P١٢٣", "nome": "X"}, 422, FORMATO_ID),
        ("post", "/produtos", {"id": "P002", "nome": "   "}, 422, "O nome do produto é obrigatório."),
        ("post", "/produtos", {"id": "P001", "nome": "X"}, 409, "Já existe um produto com o id P001."),
        ("get", "/produtos/P999", None, 404, "Produto P999 não encontrado."),
        (
            "post", "/produtos/P001/saidas", {"quantidade": 11}, 409,
            "Estoque insuficiente: foram solicitadas 11 unidades, mas só há 10 disponíveis.",
        ),
    ],
)
def test_erro_de_dominio_devolve_mensagem_simples(
    com_produto: TestClient, metodo: str, rota: str, corpo: Any, status_code: int, mensagem: str
) -> None:
    resposta = com_produto.request(metodo, rota, json=corpo)

    assert resposta.status_code == status_code
    assert resposta.json()["mensagem"] == mensagem


@pytest.mark.parametrize(
    ("metodo", "rota", "status_code", "corpo"),
    [
        ("get", "/rota-inexistente", 404, {"erro": "HTTP_404", "mensagem": "Rota não encontrada."}),
        ("delete", "/produtos", 405, {"erro": "HTTP_405", "mensagem": "Método não permitido nesta rota."}),
    ],
)
def test_erro_http_generico_devolve_mensagem_em_portugues(
    cliente: TestClient, metodo: str, rota: str, status_code: int, corpo: dict[str, str]
) -> None:
    resposta = cliente.request(metodo, rota)

    assert resposta.status_code == status_code
    assert resposta.json() == corpo
