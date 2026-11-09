import pytest

from estoque.domain.exceptions import IdProdutoInvalido, NomeProdutoInvalido
from estoque.domain.produto import Produto


@pytest.mark.parametrize("produto_id", ["P000", "P001", "P123", "P999"])
def test_criar_produto_com_id_valido(produto_id: str) -> None:
    produto = Produto(produto_id, "Teclado")

    assert produto.id == produto_id


@pytest.mark.parametrize(
    "produto_id",
    [
        "p001",
        "P01",
        "P0001",
        "P 001",
        " P001",
        "P001 ",
        "P001\n",
        "PA01",
        "X001",
        "001",
        "P",
        "",
        "P١٢٣",
        None,
        1,
    ],
)
def test_criar_produto_com_id_invalido_levanta_id_produto_invalido(produto_id: object) -> None:
    with pytest.raises(IdProdutoInvalido):
        Produto(produto_id, "Teclado")  # type: ignore[arg-type]


@pytest.mark.parametrize("nome", ["", "   ", "\t\n", None])
def test_criar_produto_com_nome_vazio_levanta_nome_produto_invalido(nome: object) -> None:
    with pytest.raises(NomeProdutoInvalido):
        Produto("P001", nome)  # type: ignore[arg-type]


def test_nome_do_produto_e_armazenado_sem_espacos_nas_pontas() -> None:
    produto = Produto("P001", "  Teclado mecânico  ")

    assert produto.nome == "Teclado mecânico"


def test_produto_novo_comeca_com_saldos_zerados() -> None:
    produto = Produto("P001", "Teclado")

    assert (produto.total, produto.disponivel, produto.reservado, produto.bloqueado) == (0, 0, 0, 0)
    assert produto.reservas == []
    assert produto.bloqueios == []
