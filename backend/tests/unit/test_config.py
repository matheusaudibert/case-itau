import pytest

from estoque.config import carregar_config


def test_config_usa_padroes_sem_variaveis_de_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in ("DATABASE_URL", "CORS_ORIGINS", "SEED_ON_STARTUP"):
        monkeypatch.delenv(nome, raising=False)

    config = carregar_config()

    assert config.database_url == "sqlite:///./data/estoque.db"
    assert config.cors_origins == ["http://localhost:4200"]
    assert config.seed_on_startup is True


def test_config_le_variaveis_de_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./outro.db")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com")
    monkeypatch.setenv("SEED_ON_STARTUP", "False")

    config = carregar_config()

    assert config.database_url == "sqlite:///./outro.db"
    assert config.cors_origins == ["http://a.com", "http://b.com"]
    assert config.seed_on_startup is False


@pytest.mark.parametrize(("valor", "esperado"), [("true", True), ("TRUE", True), (" false ", False), ("False", False)])
def test_seed_on_startup_aceita_true_ou_false_sem_diferenciar_maiusculas(
    monkeypatch: pytest.MonkeyPatch, valor: str, esperado: bool
) -> None:
    monkeypatch.setenv("SEED_ON_STARTUP", valor)

    assert carregar_config().seed_on_startup is esperado


@pytest.mark.parametrize("valor", ["talvez", "1", "0", "sim", "não", "yes", "no", ""])
def test_seed_on_startup_com_valor_invalido_levanta_erro(monkeypatch: pytest.MonkeyPatch, valor: str) -> None:
    monkeypatch.setenv("SEED_ON_STARTUP", valor)

    with pytest.raises(ValueError):
        carregar_config()
