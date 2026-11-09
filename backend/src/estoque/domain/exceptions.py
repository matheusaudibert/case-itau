from uuid import UUID


class ErroDominio(Exception):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class QuantidadeInvalida(ErroDominio):
    def __init__(self, quantidade: object) -> None:
        super().__init__("A quantidade deve ser um número inteiro maior que zero.")
        self.quantidade = quantidade


class EstoqueInsuficiente(ErroDominio):
    def __init__(self, solicitado: int, disponivel: int) -> None:
        super().__init__(f"Estoque insuficiente: foram solicitadas {solicitado} unidades, mas só há {disponivel} disponíveis.")
        self.solicitado = solicitado
        self.disponivel = disponivel


class IdProdutoInvalido(ErroDominio):
    def __init__(self, produto_id: object) -> None:
        super().__init__('O id deve seguir o formato "P000": letra P maiúscula seguida de 3 dígitos (ex.: P001).')
        self.produto_id = produto_id


class NomeProdutoInvalido(ErroDominio):
    def __init__(self) -> None:
        super().__init__("O nome do produto é obrigatório.")


class ProdutoNaoEncontrado(ErroDominio):
    def __init__(self, produto_id: str) -> None:
        super().__init__(f"Produto {produto_id} não encontrado.")


class ProdutoJaExiste(ErroDominio):
    def __init__(self, produto_id: str) -> None:
        super().__init__(f"Já existe um produto com o id {produto_id}.")


class ReservaNaoEncontrada(ErroDominio):
    def __init__(self, reserva_id: UUID) -> None:
        super().__init__(f"Reserva {reserva_id} não encontrada.")


class BloqueioNaoEncontrado(ErroDominio):
    def __init__(self, bloqueio_id: UUID) -> None:
        super().__init__(f"Bloqueio {bloqueio_id} não encontrado.")


class ReservaJaLiberada(ErroDominio):
    def __init__(self, reserva_id: UUID) -> None:
        super().__init__(f"Reserva {reserva_id} já foi liberada.")


class BloqueioJaLiberado(ErroDominio):
    def __init__(self, bloqueio_id: UUID) -> None:
        super().__init__(f"Bloqueio {bloqueio_id} já foi liberado.")


class ConflitoDeConcorrencia(ErroDominio):
    def __init__(self) -> None:
        super().__init__("O produto foi alterado por outra operação ao mesmo tempo. Tente novamente.")
