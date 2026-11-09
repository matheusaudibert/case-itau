from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Dialect, Enum, ForeignKey, String, TypeDecorator, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from estoque.domain.produto import Status


class DataHoraUTC(TypeDecorator[datetime]):
    """Grava em UTC sem fuso e devolve com fuso UTC (o SQLite não guarda fuso)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class ProdutoModel(Base):
    """`version` é incrementada pelo repositório a cada gravação (ver `RepositorioSqlAlchemy.salvar`)."""

    __tablename__ = "produtos"
    __table_args__ = (CheckConstraint("total >= 0", name="ck_produtos_total_nao_negativo"),)

    id: Mapped[str] = mapped_column(String(4), primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    total: Mapped[int]
    version: Mapped[int] = mapped_column()

    reservas: Mapped[list["ReservaModel"]] = relationship(
        back_populates="produto", cascade="all, delete-orphan", lazy="selectin", order_by="ReservaModel.criado_em"
    )
    bloqueios: Mapped[list["BloqueioModel"]] = relationship(
        back_populates="produto", cascade="all, delete-orphan", lazy="selectin", order_by="BloqueioModel.criado_em"
    )

    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class ReservaModel(Base):
    __tablename__ = "reservas"
    __table_args__ = (CheckConstraint("quantidade > 0", name="ck_reservas_quantidade_positiva"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    produto_id: Mapped[str] = mapped_column(ForeignKey("produtos.id"), index=True)
    quantidade: Mapped[int]
    motivo: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[Status] = mapped_column(Enum(Status, native_enum=False, length=10))
    criado_em: Mapped[datetime] = mapped_column(DataHoraUTC)
    liberado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC)

    produto: Mapped[ProdutoModel] = relationship(back_populates="reservas")


class BloqueioModel(Base):
    __tablename__ = "bloqueios"
    __table_args__ = (CheckConstraint("quantidade > 0", name="ck_bloqueios_quantidade_positiva"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    produto_id: Mapped[str] = mapped_column(ForeignKey("produtos.id"), index=True)
    quantidade: Mapped[int]
    motivo: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[Status] = mapped_column(Enum(Status, native_enum=False, length=10))
    criado_em: Mapped[datetime] = mapped_column(DataHoraUTC)
    liberado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC)

    produto: Mapped[ProdutoModel] = relationship(back_populates="bloqueios")
