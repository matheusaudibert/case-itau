from estoque.application.services import ServicoEstoque
from estoque.domain.exceptions import ProdutoJaExiste


def popular_banco(servico: ServicoEstoque) -> bool:
    """Cria os dados iniciais fixos pelos casos de uso, só se não houver produtos.

    Devolve se o banco foi populado. Se outro processo começar o seed ao mesmo
    tempo, `ProdutoJaExiste` no primeiro produto indica que ele já está cuidando disso.
    """
    if servico.listar_produtos():
        return False

    try:
        servico.criar_produto("P001", "Teclado mecânico")
    except ProdutoJaExiste:
        return False
    servico.entrada("P001", 100)
    servico.reservar("P001", 10, "Reserva para Matheus")
    servico.reservar("P001", 5, "Reserva de pré-venda para Julia")
    servico.bloquear("P001", 8, "Avaria")

    servico.criar_produto("P002", "Mouse sem fio")
    servico.entrada("P002", 50)
    return True
