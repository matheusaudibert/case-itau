from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from estoque.domain.exceptions import ProdutoJaExiste
from estoque.domain.produto import Bloqueio, Produto, Reserva
from estoque.infra.models import BloqueioModel, ProdutoModel, ReservaModel

VERSAO_INICIAL = 1


class RepositorioSqlAlchemy:
    """Converte entre modelos SQLAlchemy e o agregado `Produto`.

    Guarda referência aos modelos carregados: o mapa de identidade da sessão
    é fraco, e sem isso o modelo seria descartado e `salvar` o leria de novo,
    perdendo a versão vista na leitura (e com ela a detecção de conflito).
    """

    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao
        self.carregados: dict[str, ProdutoModel] = {}

    def obter(self, produto_id: str) -> Produto | None:
        modelo = self.carregados.get(produto_id) or self.sessao.get(ProdutoModel, produto_id)
        if modelo is None:
            return None
        self.carregados[modelo.id] = modelo
        return para_produto(modelo)

    def listar(self) -> list[Produto]:
        modelos = self.sessao.scalars(select(ProdutoModel).order_by(ProdutoModel.id))
        return [para_produto(m) for m in modelos]

    def adicionar(self, produto: Produto) -> None:
        """Faz flush na hora para que id duplicado vire `ProdutoJaExiste`, inclusive em criações simultâneas."""
        modelo = ProdutoModel(id=produto.id, nome=produto.nome, total=produto.total, version=VERSAO_INICIAL)
        sincronizar_filhos(modelo, produto)
        self.sessao.add(modelo)
        self.carregados[modelo.id] = modelo
        try:
            self.sessao.flush()
        except IntegrityError as erro:
            raise ProdutoJaExiste(produto.id) from erro

    def salvar(self, produto: Produto) -> None:
        """Grava o agregado e incrementa `version` sempre.

        Como o `version_id_col` só é checado quando a linha de `produtos`
        sofre UPDATE, incrementar a versão garante esse UPDATE (com
        `WHERE version = <versão lida>`) mesmo quando só reservas ou
        bloqueios mudaram.
        """
        modelo = self.carregados.get(produto.id)
        if modelo is None:
            raise LookupError(f"Produto {produto.id} precisa ser carregado com obter() antes de salvar().")
        modelo.nome = produto.nome
        modelo.total = produto.total
        modelo.version += 1
        sincronizar_filhos(modelo, produto)

    def obter_reserva(self, reserva_id: UUID) -> Reserva | None:
        modelo = self.sessao.get(ReservaModel, reserva_id)
        return para_reserva(modelo) if modelo is not None else None

    def obter_bloqueio(self, bloqueio_id: UUID) -> Bloqueio | None:
        modelo = self.sessao.get(BloqueioModel, bloqueio_id)
        return para_bloqueio(modelo) if modelo is not None else None


def sincronizar_filhos(modelo: ProdutoModel, produto: Produto) -> None:
    """Atualiza status/liberado_em das existentes e insere as novas (reservas e bloqueios nunca são apagados)."""
    reservas = {r.id: r for r in modelo.reservas}
    for reserva in produto.reservas:
        if reserva.id in reservas:
            reservas[reserva.id].status = reserva.status
            reservas[reserva.id].liberado_em = reserva.liberado_em
        else:
            modelo.reservas.append(para_reserva_model(reserva))

    bloqueios = {b.id: b for b in modelo.bloqueios}
    for bloqueio in produto.bloqueios:
        if bloqueio.id in bloqueios:
            bloqueios[bloqueio.id].status = bloqueio.status
            bloqueios[bloqueio.id].liberado_em = bloqueio.liberado_em
        else:
            modelo.bloqueios.append(para_bloqueio_model(bloqueio))


def para_produto(modelo: ProdutoModel) -> Produto:
    return Produto(
        modelo.id,
        modelo.nome,
        total=modelo.total,
        reservas=[para_reserva(r) for r in modelo.reservas],
        bloqueios=[para_bloqueio(b) for b in modelo.bloqueios],
    )


def para_reserva(modelo: ReservaModel) -> Reserva:
    return Reserva(
        id=modelo.id,
        produto_id=modelo.produto_id,
        quantidade=modelo.quantidade,
        motivo=modelo.motivo,
        status=modelo.status,
        criado_em=modelo.criado_em,
        liberado_em=modelo.liberado_em,
    )


def para_bloqueio(modelo: BloqueioModel) -> Bloqueio:
    return Bloqueio(
        id=modelo.id,
        produto_id=modelo.produto_id,
        quantidade=modelo.quantidade,
        motivo=modelo.motivo,
        status=modelo.status,
        criado_em=modelo.criado_em,
        liberado_em=modelo.liberado_em,
    )


def para_reserva_model(reserva: Reserva) -> ReservaModel:
    return ReservaModel(
        id=reserva.id,
        produto_id=reserva.produto_id,
        quantidade=reserva.quantidade,
        motivo=reserva.motivo,
        status=reserva.status,
        criado_em=reserva.criado_em,
        liberado_em=reserva.liberado_em,
    )


def para_bloqueio_model(bloqueio: Bloqueio) -> BloqueioModel:
    return BloqueioModel(
        id=bloqueio.id,
        produto_id=bloqueio.produto_id,
        quantidade=bloqueio.quantidade,
        motivo=bloqueio.motivo,
        status=bloqueio.status,
        criado_em=bloqueio.criado_em,
        liberado_em=bloqueio.liberado_em,
    )
