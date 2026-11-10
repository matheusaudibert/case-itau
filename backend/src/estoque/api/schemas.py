"""Schemas da API.

As restrições aqui (pattern do id, quantidade > 0) só documentam o contrato
no Swagger e barram entradas malformadas cedo; as regras valem no domínio.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from estoque.domain.produto import Status

Quantidade = Annotated[int, Field(strict=True, gt=0, examples=[10])]


class ProdutoCriar(BaseModel):
    id: str = Field(pattern=r"^P\d{3}$", examples=["P003"])
    nome: str = Field(min_length=1, max_length=200, examples=["Monitor 27"])


class MovimentacaoCriar(BaseModel):
    quantidade: Quantidade


class ReservaCriar(BaseModel):
    quantidade: Quantidade
    motivo: str | None = Field(default=None, max_length=200, examples=["Reserva para Matheus"])


class BloqueioCriar(BaseModel):
    quantidade: Quantidade
    motivo: str | None = Field(default=None, max_length=200, examples=["Avaria"])


class ProdutoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(examples=["P001"])
    nome: str = Field(examples=["Teclado mecânico"])
    total: int = Field(examples=[100])
    disponivel: int = Field(examples=[77])
    reservado: int = Field(examples=[15])
    bloqueado: int = Field(examples=[8])


class ReservaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    produto_id: str = Field(examples=["P001"])
    quantidade: int = Field(examples=[10])
    motivo: str | None = Field(examples=["Reserva para Matheus"])
    status: Status = Field(examples=[Status.ATIVO])
    criado_em: datetime = Field(examples=["2026-11-09T03:00:00Z"])
    liberado_em: datetime | None = Field(examples=[None])


class BloqueioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"])
    produto_id: str = Field(examples=["P001"])
    quantidade: int = Field(examples=[8])
    motivo: str | None = Field(examples=["Avaria"])
    status: Status = Field(examples=[Status.ATIVO])
    criado_em: datetime = Field(examples=["2026-11-09T03:00:00Z"])
    liberado_em: datetime | None = Field(examples=[None])


class ErroSaida(BaseModel):
    erro: str
    mensagem: str
