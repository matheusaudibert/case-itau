from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from estoque.api.main import criar_app
from estoque.application.services import ServicoEstoque
from estoque.config import Config
from estoque.domain.produto import Status
from estoque.infra.seed import popular_banco
from tests.unit.saldos import saldos


def test_seed_cria_p001_com_reservas_e_bloqueio(servico: ServicoEstoque) -> None:
    assert popular_banco(servico) is True

    produto = servico.consultar_produto("P001")
    assert produto.nome == "Teclado mecânico"
    assert saldos(produto) == (100, 77, 15, 8)

    reservas = servico.listar_reservas("P001", Status.ATIVO)
    assert sorted((r.motivo, r.quantidade) for r in reservas) == [
        ("Reserva de pré-venda para Julia", 5),
        ("Reserva para Matheus", 10),
    ]
    assert len(servico.listar_reservas("P001")) == 2

    bloqueios = servico.listar_bloqueios("P001", Status.ATIVO)
    assert [(b.quantidade, b.motivo) for b in bloqueios] == [(8, "Avaria")]
    assert len(servico.listar_bloqueios("P001")) == 1


def test_seed_cria_p002_sem_reservas_nem_bloqueios(servico: ServicoEstoque) -> None:
    popular_banco(servico)

    produto = servico.consultar_produto("P002")
    assert produto.nome == "Mouse sem fio"
    assert saldos(produto) == (50, 50, 0, 0)
    assert servico.listar_reservas("P002") == []
    assert servico.listar_bloqueios("P002") == []


def test_seed_duas_vezes_nao_duplica_nada(servico: ServicoEstoque) -> None:
    assert popular_banco(servico) is True
    assert popular_banco(servico) is False

    assert [p.id for p in servico.listar_produtos()] == ["P001", "P002"]
    assert saldos(servico.consultar_produto("P001")) == (100, 77, 15, 8)
    assert saldos(servico.consultar_produto("P002")) == (50, 50, 0, 0)
    assert len(servico.listar_reservas("P001")) == 2
    assert len(servico.listar_bloqueios("P001")) == 1


def test_seed_nao_roda_se_ja_existe_algum_produto(servico: ServicoEstoque) -> None:
    servico.criar_produto("P050", "Cadastrado antes")

    assert popular_banco(servico) is False
    assert [p.id for p in servico.listar_produtos()] == ["P050"]


def criar_config(database_url: str, seed_on_startup: bool) -> Config:
    return Config(database_url=database_url, cors_origins=["http://localhost:4200"], seed_on_startup=seed_on_startup)


def test_api_com_seed_on_startup_true_sobe_com_os_dados_do_seed(database_url: str) -> None:
    with TestClient(criar_app(criar_config(database_url, seed_on_startup=True))) as cliente:
        produtos = {p["id"]: p for p in cliente.get("/produtos").json()}

    assert set(produtos) == {"P001", "P002"}
    assert (produtos["P001"]["reservado"], produtos["P001"]["bloqueado"], produtos["P001"]["disponivel"]) == (15, 8, 77)
    assert produtos["P002"]["disponivel"] == 50


def test_api_reiniciada_com_seed_nao_duplica(database_url: str) -> None:
    for inicializacao in range(2):
        with TestClient(criar_app(criar_config(database_url, seed_on_startup=True))) as cliente:
            produtos = cliente.get("/produtos").json()
            reservas = cliente.get("/produtos/P001/reservas").json()

    assert [p["id"] for p in produtos] == ["P001", "P002"]
    assert len(reservas) == 2


def test_api_com_seed_on_startup_false_sobe_sem_produtos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lê a configuração das variáveis de ambiente, como em produção."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sem_seed.db'}")
    monkeypatch.setenv("SEED_ON_STARTUP", "false")

    with TestClient(criar_app()) as cliente:
        resposta = cliente.get("/produtos")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_fixture_cliente_dos_demais_testes_nao_roda_o_seed(cliente: TestClient) -> None:
    assert cliente.get("/produtos").json() == []
