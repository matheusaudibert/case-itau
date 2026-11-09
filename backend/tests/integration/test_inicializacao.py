from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from estoque.api.main import criar_app
from estoque.config import Config
from estoque.infra.database import criar_engine


def criar_config(database_url: str) -> Config:
    return Config(database_url=database_url, cors_origins=["http://localhost:4200"], seed_on_startup=False)


def test_inicializacao_cria_pasta_do_sqlite_inexistente(tmp_path: Path) -> None:
    arquivo = tmp_path / "nao" / "existe" / "estoque.db"

    with TestClient(criar_app(criar_config(f"sqlite:///{arquivo}"))) as cliente:
        assert cliente.get("/produtos").status_code == 200

    assert arquivo.is_file()


def test_inicializacao_com_caminho_relativo_padrao_cria_data_no_diretorio_atual(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simula o primeiro `uvicorn` logo após o clone, sem a pasta `data/`."""
    monkeypatch.chdir(tmp_path)

    with TestClient(criar_app(criar_config("sqlite:///./data/estoque.db"))) as cliente:
        assert cliente.post("/produtos", json={"id": "P001", "nome": "Teclado"}).status_code == 201

    assert (tmp_path / "data" / "estoque.db").is_file()


def test_inicializacao_com_pasta_ja_existente_reaproveita_o_banco(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'estoque.db'}"
    with TestClient(criar_app(criar_config(url))) as cliente:
        cliente.post("/produtos", json={"id": "P001", "nome": "Teclado"})

    with TestClient(criar_app(criar_config(url))) as cliente:
        assert [p["id"] for p in cliente.get("/produtos").json()] == ["P001"]


@pytest.mark.parametrize("database_url", ["sqlite://", "sqlite:///:memory:"])
def test_sqlite_em_memoria_nao_cria_pasta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    monkeypatch.chdir(tmp_path)

    criar_engine(database_url).dispose()

    assert list(tmp_path.iterdir()) == []
