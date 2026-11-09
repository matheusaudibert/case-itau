from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from estoque.api.errors import documentar_erros
from estoque.api.schemas import (
    BloqueioCriar,
    BloqueioSaida,
    MovimentacaoCriar,
    ProdutoCriar,
    ProdutoSaida,
    ReservaCriar,
    ReservaSaida,
)
from estoque.application.ports import UnitOfWork
from estoque.application.services import ServicoEstoque
from estoque.domain.exceptions import (
    BloqueioJaLiberado,
    BloqueioNaoEncontrado,
    ConflitoDeConcorrencia,
    EstoqueInsuficiente,
    IdProdutoInvalido,
    NomeProdutoInvalido,
    ProdutoJaExiste,
    ProdutoNaoEncontrado,
    ReservaJaLiberada,
    ReservaNaoEncontrada,
)
from estoque.domain.produto import Status


def obter_fabrica_uow(request: Request) -> Callable[[], UnitOfWork]:
    """Ponto de injeção do Unit of Work; os testes podem substituí-lo via `dependency_overrides`."""
    return request.app.state.fabrica_uow


def obter_servico(fabrica_uow: Annotated[Callable[[], UnitOfWork], Depends(obter_fabrica_uow)]) -> ServicoEstoque:
    return ServicoEstoque(fabrica_uow)


Servico = Annotated[ServicoEstoque, Depends(obter_servico)]

router = APIRouter()


@router.post(
    "/produtos", status_code=status.HTTP_201_CREATED, tags=["produtos"],
    responses=documentar_erros(ProdutoJaExiste, IdProdutoInvalido, NomeProdutoInvalido, validacao="id"),
)
def criar_produto(dados: ProdutoCriar, servico: Servico) -> ProdutoSaida:
    return ProdutoSaida.model_validate(servico.criar_produto(dados.id, dados.nome))


@router.get("/produtos", tags=["produtos"])
def listar_produtos(servico: Servico) -> list[ProdutoSaida]:
    return [ProdutoSaida.model_validate(p) for p in servico.listar_produtos()]


@router.get(
    "/produtos/{produto_id}", tags=["produtos"],
    responses=documentar_erros(ProdutoNaoEncontrado),
)
def consultar_produto(produto_id: str, servico: Servico) -> ProdutoSaida:
    return ProdutoSaida.model_validate(servico.consultar_produto(produto_id))


@router.post(
    "/produtos/{produto_id}/entradas", tags=["produtos"],
    responses=documentar_erros(ProdutoNaoEncontrado, ConflitoDeConcorrencia, validacao="quantidade"),
)
def registrar_entrada(produto_id: str, dados: MovimentacaoCriar, servico: Servico) -> ProdutoSaida:
    return ProdutoSaida.model_validate(servico.entrada(produto_id, dados.quantidade))


@router.post(
    "/produtos/{produto_id}/saidas", tags=["produtos"],
    responses=documentar_erros(ProdutoNaoEncontrado, EstoqueInsuficiente, ConflitoDeConcorrencia, validacao="quantidade"),
)
def registrar_saida(produto_id: str, dados: MovimentacaoCriar, servico: Servico) -> ProdutoSaida:
    return ProdutoSaida.model_validate(servico.saida(produto_id, dados.quantidade))


@router.post(
    "/produtos/{produto_id}/reservas", status_code=status.HTTP_201_CREATED, tags=["reservas"],
    responses=documentar_erros(ProdutoNaoEncontrado, EstoqueInsuficiente, ConflitoDeConcorrencia, validacao="quantidade"),
)
def reservar(produto_id: str, dados: ReservaCriar, servico: Servico) -> ReservaSaida:
    return ReservaSaida.model_validate(servico.reservar(produto_id, dados.quantidade, dados.motivo))


@router.get(
    "/produtos/{produto_id}/reservas", tags=["reservas"],
    responses=documentar_erros(ProdutoNaoEncontrado, validacao="status"),
)
def listar_reservas(produto_id: str, servico: Servico, status: Status | None = None) -> list[ReservaSaida]:
    return [ReservaSaida.model_validate(r) for r in servico.listar_reservas(produto_id, status)]


@router.get(
    "/reservas/{reserva_id}", tags=["reservas"],
    responses=documentar_erros(ReservaNaoEncontrada, validacao="reserva_id"),
)
def consultar_reserva(reserva_id: UUID, servico: Servico) -> ReservaSaida:
    return ReservaSaida.model_validate(servico.consultar_reserva(reserva_id))


@router.post(
    "/reservas/{reserva_id}/liberar", tags=["reservas"],
    responses=documentar_erros(ReservaNaoEncontrada, ReservaJaLiberada, ConflitoDeConcorrencia, validacao="reserva_id"),
)
def liberar_reserva(reserva_id: UUID, servico: Servico) -> ReservaSaida:
    return ReservaSaida.model_validate(servico.liberar_reserva(reserva_id))


@router.post(
    "/produtos/{produto_id}/bloqueios", status_code=status.HTTP_201_CREATED, tags=["bloqueios"],
    responses=documentar_erros(ProdutoNaoEncontrado, EstoqueInsuficiente, ConflitoDeConcorrencia, validacao="quantidade"),
)
def bloquear(produto_id: str, dados: BloqueioCriar, servico: Servico) -> BloqueioSaida:
    return BloqueioSaida.model_validate(servico.bloquear(produto_id, dados.quantidade, dados.motivo))


@router.get(
    "/produtos/{produto_id}/bloqueios", tags=["bloqueios"],
    responses=documentar_erros(ProdutoNaoEncontrado, validacao="status"),
)
def listar_bloqueios(produto_id: str, servico: Servico, status: Status | None = None) -> list[BloqueioSaida]:
    return [BloqueioSaida.model_validate(b) for b in servico.listar_bloqueios(produto_id, status)]


@router.get(
    "/bloqueios/{bloqueio_id}", tags=["bloqueios"],
    responses=documentar_erros(BloqueioNaoEncontrado, validacao="bloqueio_id"),
)
def consultar_bloqueio(bloqueio_id: UUID, servico: Servico) -> BloqueioSaida:
    return BloqueioSaida.model_validate(servico.consultar_bloqueio(bloqueio_id))


@router.post(
    "/bloqueios/{bloqueio_id}/liberar", tags=["bloqueios"],
    responses=documentar_erros(BloqueioNaoEncontrado, BloqueioJaLiberado, ConflitoDeConcorrencia, validacao="bloqueio_id"),
)
def liberar_bloqueio(bloqueio_id: UUID, servico: Servico) -> BloqueioSaida:
    return BloqueioSaida.model_validate(servico.liberar_bloqueio(bloqueio_id))
