from collections.abc import Callable
from uuid import UUID

from estoque.application.ports import ConflitoDeVersao, UnitOfWork
from estoque.domain.exceptions import (
    BloqueioNaoEncontrado,
    ConflitoDeConcorrencia,
    ProdutoJaExiste,
    ProdutoNaoEncontrado,
    ReservaNaoEncontrada,
)
from estoque.domain.produto import Bloqueio, Produto, Reserva, Status

MAX_TENTATIVAS = 3


class ServicoEstoque:
    """Casos de uso do estoque. Cada método roda em uma transação própria."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self.uow_factory = uow_factory

    def criar_produto(self, produto_id: str, nome: str) -> Produto:
        produto = Produto(produto_id, nome)
        with self.uow_factory() as uow:
            if uow.produtos.obter(produto.id) is not None:
                raise ProdutoJaExiste(produto.id)
            uow.produtos.adicionar(produto)
            uow.commit()
        return produto

    def listar_produtos(self) -> list[Produto]:
        with self.uow_factory() as uow:
            return uow.produtos.listar()

    def consultar_produto(self, produto_id: str) -> Produto:
        with self.uow_factory() as uow:
            return carregar_produto(uow, produto_id)

    def entrada(self, produto_id: str, quantidade: int) -> Produto:
        def operacao(uow: UnitOfWork) -> Produto:
            produto = carregar_produto(uow, produto_id)
            produto.entrada(quantidade)
            uow.produtos.salvar(produto)
            return produto

        return self.executar_com_retry(operacao)

    def saida(self, produto_id: str, quantidade: int) -> Produto:
        def operacao(uow: UnitOfWork) -> Produto:
            produto = carregar_produto(uow, produto_id)
            produto.saida(quantidade)
            uow.produtos.salvar(produto)
            return produto

        return self.executar_com_retry(operacao)

    def reservar(self, produto_id: str, quantidade: int, motivo: str | None = None) -> Reserva:
        def operacao(uow: UnitOfWork) -> Reserva:
            produto = carregar_produto(uow, produto_id)
            reserva = produto.reservar(quantidade, motivo)
            uow.produtos.salvar(produto)
            return reserva

        return self.executar_com_retry(operacao)

    def bloquear(self, produto_id: str, quantidade: int, motivo: str | None = None) -> Bloqueio:
        def operacao(uow: UnitOfWork) -> Bloqueio:
            produto = carregar_produto(uow, produto_id)
            bloqueio = produto.bloquear(quantidade, motivo)
            uow.produtos.salvar(produto)
            return bloqueio

        return self.executar_com_retry(operacao)

    def liberar_reserva(self, reserva_id: UUID) -> Reserva:
        def operacao(uow: UnitOfWork) -> Reserva:
            reserva = carregar_reserva(uow, reserva_id)
            produto = carregar_produto(uow, reserva.produto_id)
            liberada = produto.liberar_reserva(reserva_id)
            uow.produtos.salvar(produto)
            return liberada

        return self.executar_com_retry(operacao)

    def liberar_bloqueio(self, bloqueio_id: UUID) -> Bloqueio:
        def operacao(uow: UnitOfWork) -> Bloqueio:
            bloqueio = carregar_bloqueio(uow, bloqueio_id)
            produto = carregar_produto(uow, bloqueio.produto_id)
            liberado = produto.liberar_bloqueio(bloqueio_id)
            uow.produtos.salvar(produto)
            return liberado

        return self.executar_com_retry(operacao)

    def consultar_reserva(self, reserva_id: UUID) -> Reserva:
        with self.uow_factory() as uow:
            return carregar_reserva(uow, reserva_id)

    def consultar_bloqueio(self, bloqueio_id: UUID) -> Bloqueio:
        with self.uow_factory() as uow:
            return carregar_bloqueio(uow, bloqueio_id)

    def listar_reservas(self, produto_id: str, status: Status | None = None) -> list[Reserva]:
        with self.uow_factory() as uow:
            produto = carregar_produto(uow, produto_id)
            return filtrar_por_status(produto.reservas, status)

    def listar_bloqueios(self, produto_id: str, status: Status | None = None) -> list[Bloqueio]:
        with self.uow_factory() as uow:
            produto = carregar_produto(uow, produto_id)
            return filtrar_por_status(produto.bloqueios, status)

    def executar_com_retry[T](self, operacao: Callable[[UnitOfWork], T]) -> T:
        """Roda a operação numa transação nova a cada tentativa.

        Em `ConflitoDeVersao` o produto é recarregado do banco e a regra é
        reavaliada sobre o estado atual. Erros de domínio não são repetidos.
        """
        for tentativa in range(MAX_TENTATIVAS):
            try:
                with self.uow_factory() as uow:
                    resultado = operacao(uow)
                    uow.commit()
                    return resultado
            except ConflitoDeVersao:
                continue
        raise ConflitoDeConcorrencia()


def carregar_produto(uow: UnitOfWork, produto_id: str) -> Produto:
    produto = uow.produtos.obter(produto_id)
    if produto is None:
        raise ProdutoNaoEncontrado(produto_id)
    return produto


def carregar_reserva(uow: UnitOfWork, reserva_id: UUID) -> Reserva:
    reserva = uow.produtos.obter_reserva(reserva_id)
    if reserva is None:
        raise ReservaNaoEncontrada(reserva_id)
    return reserva


def carregar_bloqueio(uow: UnitOfWork, bloqueio_id: UUID) -> Bloqueio:
    bloqueio = uow.produtos.obter_bloqueio(bloqueio_id)
    if bloqueio is None:
        raise BloqueioNaoEncontrado(bloqueio_id)
    return bloqueio


def filtrar_por_status[R: (Reserva, Bloqueio)](registros: list[R], status: Status | None) -> list[R]:
    selecionados = [r for r in registros if status is None or r.status is status]
    return sorted(selecionados, key=lambda r: r.criado_em)
