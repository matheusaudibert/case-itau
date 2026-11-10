from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from estoque.api.errors import STATUS_POR_ERRO, codigo_do_erro
from estoque.domain import exceptions

Json = dict[str, Any]


def saldos(cliente: TestClient, produto_id: str = "P001") -> Json:
    resposta = cliente.get(f"/produtos/{produto_id}")
    assert resposta.status_code == 200
    corpo = resposta.json()
    return {chave: corpo[chave] for chave in ("total", "disponivel", "reservado", "bloqueado")}


def saldos_esperados(total: int, disponivel: int, reservado: int, bloqueado: int) -> Json:
    return {"total": total, "disponivel": disponivel, "reservado": reservado, "bloqueado": bloqueado}


def assert_erro(resposta: Any, status_code: int, erro: str) -> None:
    assert resposta.status_code == status_code
    corpo = resposta.json()
    assert set(corpo) == {"erro", "mensagem"}
    assert corpo["erro"] == erro
    assert isinstance(corpo["mensagem"], str) and corpo["mensagem"]


@pytest.fixture
def com_produto(cliente: TestClient) -> TestClient:
    """P001 com total 100, reservas de 10 e 5 e bloqueio de 8 (disponível 77)."""
    assert cliente.post("/produtos", json={"id": "P001", "nome": "Teclado mecânico"}).status_code == 201
    assert cliente.post("/produtos/P001/entradas", json={"quantidade": 100}).status_code == 200
    assert cliente.post("/produtos/P001/reservas", json={"quantidade": 10, "motivo": "Reserva 001"}).status_code == 201
    assert cliente.post("/produtos/P001/reservas", json={"quantidade": 5, "motivo": "Reserva 002"}).status_code == 201
    assert cliente.post("/produtos/P001/bloqueios", json={"quantidade": 8, "motivo": "Avaria"}).status_code == 201
    return cliente


def obter_reserva_id(cliente: TestClient, motivo: str = "Reserva 001") -> str:
    reservas = cliente.get("/produtos/P001/reservas").json()
    return next(r["id"] for r in reservas if r["motivo"] == motivo)


def obter_bloqueio_id(cliente: TestClient) -> str:
    return cliente.get("/produtos/P001/bloqueios").json()[0]["id"]


# --- sucesso --------------------------------------------------------------


def test_criar_produto_devolve_201_com_saldos_zerados(cliente: TestClient) -> None:
    resposta = cliente.post("/produtos", json={"id": "P001", "nome": "Teclado mecânico"})

    assert resposta.status_code == 201
    assert resposta.json() == {
        "id": "P001",
        "nome": "Teclado mecânico",
        "total": 0,
        "disponivel": 0,
        "reservado": 0,
        "bloqueado": 0,
    }


def test_listar_produtos(com_produto: TestClient) -> None:
    com_produto.post("/produtos", json={"id": "P002", "nome": "Mouse sem fio"})

    resposta = com_produto.get("/produtos")

    assert resposta.status_code == 200
    assert [(p["id"], p["disponivel"]) for p in resposta.json()] == [("P001", 77), ("P002", 0)]


def test_listar_produtos_vazio(cliente: TestClient) -> None:
    resposta = cliente.get("/produtos")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_consultar_produto(com_produto: TestClient) -> None:
    resposta = com_produto.get("/produtos/P001")

    assert resposta.status_code == 200
    assert resposta.json() == {"id": "P001", "nome": "Teclado mecânico", **saldos_esperados(100, 77, 15, 8)}


def test_entrada_devolve_produto_atualizado(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos/P001/entradas", json={"quantidade": 20})

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 120
    assert resposta.json()["disponivel"] == 97


def test_saida_devolve_produto_atualizado(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos/P001/saidas", json={"quantidade": 7})

    assert resposta.status_code == 200
    assert {k: resposta.json()[k] for k in ("total", "disponivel", "reservado", "bloqueado")} == saldos_esperados(
        93, 70, 15, 8
    )


def test_reservar_devolve_201_com_a_reserva(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos/P001/reservas", json={"quantidade": 12, "motivo": "Reserva 003"})

    assert resposta.status_code == 201
    corpo = resposta.json()
    UUID(corpo["id"])
    assert corpo["produto_id"] == "P001"
    assert corpo["quantidade"] == 12
    assert corpo["motivo"] == "Reserva 003"
    assert corpo["status"] == "ATIVO"
    assert corpo["criado_em"]
    assert corpo["liberado_em"] is None
    assert saldos(com_produto) == saldos_esperados(100, 65, 27, 8)


def test_bloquear_devolve_201_com_o_bloqueio(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos/P001/bloqueios", json={"quantidade": 4, "motivo": "Inventário"})

    assert resposta.status_code == 201
    corpo = resposta.json()
    UUID(corpo["id"])
    assert corpo["motivo"] == "Inventário"
    assert corpo["status"] == "ATIVO"
    assert saldos(com_produto) == saldos_esperados(100, 73, 15, 12)


def test_bloquear_sem_motivo(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos/P001/bloqueios", json={"quantidade": 1})

    assert resposta.status_code == 201
    assert resposta.json()["motivo"] is None


def test_listar_reservas_com_e_sem_filtro_de_status(com_produto: TestClient) -> None:
    com_produto.post(f"/reservas/{obter_reserva_id(com_produto, 'Reserva 001')}/liberar")

    todas = com_produto.get("/produtos/P001/reservas")
    ativas = com_produto.get("/produtos/P001/reservas", params={"status": "ATIVO"})
    liberadas = com_produto.get("/produtos/P001/reservas", params={"status": "LIBERADO"})

    assert todas.status_code == ativas.status_code == liberadas.status_code == 200
    assert [r["motivo"] for r in todas.json()] == ["Reserva 001", "Reserva 002"]
    assert [r["motivo"] for r in ativas.json()] == ["Reserva 002"]
    assert [r["motivo"] for r in liberadas.json()] == ["Reserva 001"]


def test_listar_bloqueios_com_filtro_de_status(com_produto: TestClient) -> None:
    resposta = com_produto.get("/produtos/P001/bloqueios", params={"status": "ATIVO"})

    assert resposta.status_code == 200
    assert [(b["quantidade"], b["motivo"]) for b in resposta.json()] == [(8, "Avaria")]


def test_consultar_reserva(com_produto: TestClient) -> None:
    reserva_id = obter_reserva_id(com_produto)

    resposta = com_produto.get(f"/reservas/{reserva_id}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == reserva_id
    assert resposta.json()["quantidade"] == 10


def test_consultar_bloqueio(com_produto: TestClient) -> None:
    bloqueio_id = obter_bloqueio_id(com_produto)

    resposta = com_produto.get(f"/bloqueios/{bloqueio_id}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == bloqueio_id
    assert resposta.json()["quantidade"] == 8


def test_liberar_reserva_devolve_reserva_liberada(com_produto: TestClient) -> None:
    resposta = com_produto.post(f"/reservas/{obter_reserva_id(com_produto)}/liberar")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "LIBERADO"
    assert resposta.json()["liberado_em"] is not None
    assert saldos(com_produto) == saldos_esperados(100, 87, 5, 8)


def test_liberar_bloqueio_devolve_bloqueio_liberado(com_produto: TestClient) -> None:
    resposta = com_produto.post(f"/bloqueios/{obter_bloqueio_id(com_produto)}/liberar")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "LIBERADO"
    assert saldos(com_produto) == saldos_esperados(100, 85, 15, 0)


# --- 404 ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("metodo", "rota", "corpo"),
    [
        ("get", "/produtos/P999", None),
        ("post", "/produtos/P999/entradas", {"quantidade": 1}),
        ("post", "/produtos/P999/saidas", {"quantidade": 1}),
        ("post", "/produtos/P999/reservas", {"quantidade": 1, "motivo": "Reserva"}),
        ("post", "/produtos/P999/bloqueios", {"quantidade": 1}),
        ("get", "/produtos/P999/reservas", None),
        ("get", "/produtos/P999/bloqueios", None),
    ],
)
def test_produto_inexistente_devolve_404(cliente: TestClient, metodo: str, rota: str, corpo: Json | None) -> None:
    resposta = cliente.request(metodo, rota, json=corpo)

    assert_erro(resposta, 404, "PRODUTO_NAO_ENCONTRADO")


@pytest.mark.parametrize(("metodo", "rota"), [("get", "/reservas/{id}"), ("post", "/reservas/{id}/liberar")])
def test_reserva_inexistente_devolve_404(cliente: TestClient, metodo: str, rota: str) -> None:
    resposta = cliente.request(metodo, rota.format(id=uuid4()))

    assert_erro(resposta, 404, "RESERVA_NAO_ENCONTRADA")


@pytest.mark.parametrize(("metodo", "rota"), [("get", "/bloqueios/{id}"), ("post", "/bloqueios/{id}/liberar")])
def test_bloqueio_inexistente_devolve_404(cliente: TestClient, metodo: str, rota: str) -> None:
    resposta = cliente.request(metodo, rota.format(id=uuid4()))

    assert_erro(resposta, 404, "BLOQUEIO_NAO_ENCONTRADO")


def test_rota_inexistente_devolve_404_no_mesmo_formato(cliente: TestClient) -> None:
    assert_erro(cliente.get("/nao-existe"), 404, "HTTP_404")


# --- 409 ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rota", "corpo"),
    [
        ("/produtos/P001/saidas", {"quantidade": 78}),
        ("/produtos/P001/reservas", {"quantidade": 78, "motivo": "Reserva 003"}),
        ("/produtos/P001/bloqueios", {"quantidade": 78}),
    ],
)
def test_acima_do_disponivel_devolve_409_e_nao_altera_saldos(com_produto: TestClient, rota: str, corpo: Json) -> None:
    resposta = com_produto.post(rota, json=corpo)

    assert_erro(resposta, 409, "ESTOQUE_INSUFICIENTE")
    assert saldos(com_produto) == saldos_esperados(100, 77, 15, 8)
    assert len(com_produto.get("/produtos/P001/reservas").json()) == 2
    assert len(com_produto.get("/produtos/P001/bloqueios").json()) == 1


def test_liberar_reserva_duas_vezes_devolve_409(com_produto: TestClient) -> None:
    reserva_id = obter_reserva_id(com_produto)
    com_produto.post(f"/reservas/{reserva_id}/liberar")

    resposta = com_produto.post(f"/reservas/{reserva_id}/liberar")

    assert_erro(resposta, 409, "RESERVA_JA_LIBERADA")
    assert saldos(com_produto) == saldos_esperados(100, 87, 5, 8)


def test_liberar_bloqueio_duas_vezes_devolve_409(com_produto: TestClient) -> None:
    bloqueio_id = obter_bloqueio_id(com_produto)
    com_produto.post(f"/bloqueios/{bloqueio_id}/liberar")

    resposta = com_produto.post(f"/bloqueios/{bloqueio_id}/liberar")

    assert_erro(resposta, 409, "BLOQUEIO_JA_LIBERADO")
    assert saldos(com_produto) == saldos_esperados(100, 85, 15, 0)


def test_criar_produto_existente_devolve_409_e_mantem_o_original(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos", json={"id": "P001", "nome": "Outro"})

    assert_erro(resposta, 409, "PRODUTO_JA_EXISTE")
    assert com_produto.get("/produtos/P001").json()["nome"] == "Teclado mecânico"
    assert saldos(com_produto) == saldos_esperados(100, 77, 15, 8)


# --- 422 ------------------------------------------------------------------


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, 5.0, "5", True, None])
@pytest.mark.parametrize(
    "rota", ["/produtos/P001/entradas", "/produtos/P001/saidas", "/produtos/P001/reservas", "/produtos/P001/bloqueios"]
)
def test_quantidade_invalida_devolve_422_e_nao_altera_saldos(
    com_produto: TestClient, rota: str, quantidade: object
) -> None:
    resposta = com_produto.post(rota, json={"quantidade": quantidade, "motivo": "Reserva 003"})

    assert_erro(resposta, 422, "VALIDACAO")
    assert "quantidade" in resposta.json()["mensagem"]
    assert saldos(com_produto) == saldos_esperados(100, 77, 15, 8)


def test_corpo_sem_quantidade_devolve_422(com_produto: TestClient) -> None:
    assert_erro(com_produto.post("/produtos/P001/entradas", json={}), 422, "VALIDACAO")


@pytest.mark.parametrize("produto_id", ["p001", "P01", "P0001", "P 001", "PA01", ""])
def test_criar_produto_com_id_fora_do_formato_devolve_422(cliente: TestClient, produto_id: str) -> None:
    resposta = cliente.post("/produtos", json={"id": produto_id, "nome": "Teclado"})

    assert_erro(resposta, 422, "VALIDACAO")
    assert "id" in resposta.json()["mensagem"]
    assert cliente.get("/produtos").json() == []


def test_id_rejeitado_pelo_dominio_devolve_422_com_codigo_de_dominio(cliente: TestClient) -> None:
    """Dígitos não ASCII passam pelo `\\d` do pattern do schema, mas o domínio os rejeita."""
    resposta = cliente.post("/produtos", json={"id": "P١٢٣", "nome": "Teclado"})

    assert_erro(resposta, 422, "ID_PRODUTO_INVALIDO")


def test_criar_produto_com_nome_vazio_devolve_422(cliente: TestClient) -> None:
    assert_erro(cliente.post("/produtos", json={"id": "P001", "nome": ""}), 422, "VALIDACAO")


def test_criar_produto_com_nome_so_de_espacos_devolve_422_do_dominio(cliente: TestClient) -> None:
    resposta = cliente.post("/produtos", json={"id": "P001", "nome": "   "})

    assert_erro(resposta, 422, "NOME_PRODUTO_INVALIDO")
    assert cliente.get("/produtos").json() == []


def test_reservar_sem_motivo_devolve_201_com_motivo_nulo(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos/P001/reservas", json={"quantidade": 1})

    assert resposta.status_code == 201
    assert resposta.json()["motivo"] is None
    assert saldos(com_produto) == saldos_esperados(100, 76, 16, 8)


def test_reserva_nao_aceita_mais_pedido_id(com_produto: TestClient) -> None:
    """Campo removido: é ignorado no corpo e não aparece na resposta."""
    resposta = com_produto.post("/produtos/P001/reservas", json={"quantidade": 1, "pedido_id": "PED-001"})

    assert resposta.status_code == 201
    assert "pedido_id" not in resposta.json()
    assert resposta.json()["motivo"] is None


def test_motivo_da_reserva_acima_de_200_caracteres_devolve_422(com_produto: TestClient) -> None:
    resposta = com_produto.post("/produtos/P001/reservas", json={"quantidade": 1, "motivo": "x" * 201})

    assert_erro(resposta, 422, "VALIDACAO")
    assert saldos(com_produto) == saldos_esperados(100, 77, 15, 8)


def test_id_de_reserva_que_nao_e_uuid_devolve_422(cliente: TestClient) -> None:
    assert_erro(cliente.get("/reservas/abc"), 422, "VALIDACAO")


def test_status_invalido_no_filtro_devolve_422(com_produto: TestClient) -> None:
    assert_erro(com_produto.get("/produtos/P001/reservas", params={"status": "QUALQUER"}), 422, "VALIDACAO")


def test_json_malformado_devolve_422(com_produto: TestClient) -> None:
    resposta = com_produto.post(
        "/produtos/P001/entradas", content="{quantidade", headers={"Content-Type": "application/json"}
    )

    assert_erro(resposta, 422, "VALIDACAO")


# --- mapeamento -----------------------------------------------------------


def test_toda_excecao_de_dominio_tem_status_http_mapeado() -> None:
    excecoes = {
        obj
        for obj in vars(exceptions).values()
        if isinstance(obj, type) and issubclass(obj, exceptions.ErroDominio) and obj is not exceptions.ErroDominio
    }

    assert excecoes == set(STATUS_POR_ERRO)


def test_codigo_do_erro_em_maiusculas_com_underscore() -> None:
    assert codigo_do_erro(exceptions.EstoqueInsuficiente) == "ESTOQUE_INSUFICIENTE"
    assert codigo_do_erro(exceptions.ProdutoNaoEncontrado) == "PRODUTO_NAO_ENCONTRADO"


def test_cors_permite_a_origem_configurada(cliente: TestClient) -> None:
    resposta = cliente.options(
        "/produtos",
        headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "POST"},
    )

    assert resposta.headers["access-control-allow-origin"] == "http://localhost:4200"


# --- fluxo completo -------------------------------------------------------


def test_fluxo_completo_com_saldos_a_cada_passo(cliente: TestClient) -> None:
    assert cliente.post("/produtos", json={"id": "P010", "nome": "Headset"}).status_code == 201
    assert saldos(cliente, "P010") == saldos_esperados(0, 0, 0, 0)

    assert cliente.post("/produtos/P010/entradas", json={"quantidade": 50}).status_code == 200
    assert saldos(cliente, "P010") == saldos_esperados(50, 50, 0, 0)

    reserva = cliente.post("/produtos/P010/reservas", json={"quantidade": 20, "motivo": "Reserva 100"})
    assert reserva.status_code == 201
    assert saldos(cliente, "P010") == saldos_esperados(50, 30, 20, 0)

    bloqueio = cliente.post("/produtos/P010/bloqueios", json={"quantidade": 10, "motivo": "Avaria"})
    assert bloqueio.status_code == 201
    assert saldos(cliente, "P010") == saldos_esperados(50, 20, 20, 10)

    assert cliente.post(f"/reservas/{reserva.json()['id']}/liberar").status_code == 200
    assert saldos(cliente, "P010") == saldos_esperados(50, 40, 0, 10)

    assert cliente.post(f"/bloqueios/{bloqueio.json()['id']}/liberar").status_code == 200
    assert saldos(cliente, "P010") == saldos_esperados(50, 50, 0, 0)

    assert cliente.get(f"/reservas/{reserva.json()['id']}").json()["status"] == "LIBERADO"
    assert cliente.get(f"/bloqueios/{bloqueio.json()['id']}").json()["status"] == "LIBERADO"
