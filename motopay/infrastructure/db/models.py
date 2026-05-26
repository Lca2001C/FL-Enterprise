from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from motopay.infrastructure.db.base import Base


class Operacao(Base):
    __tablename__ = "operacoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    multa_fixa_percentual: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="2.00", nullable=False
    )
    juros_diario_percentual: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="0.10", nullable=False
    )
    telegram_templates: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
    telegram_custom_messages: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    payment_provider: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="asaas"
    )
    mercadopago_access_token: Mapped[str | None] = mapped_column(String(512), nullable=True)

    usuarios: Mapped[list[Usuario]] = relationship(back_populates="operacao")
    motos: Mapped[list[Moto]] = relationship(back_populates="operacao")
    clientes: Mapped[list[Cliente]] = relationship(back_populates="operacao")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    operacao_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("operacoes.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    operacao: Mapped[Operacao | None] = relationship(back_populates="usuarios")


class Moto(Base):
    __tablename__ = "motos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    placa: Mapped[str] = mapped_column(String(16), nullable=False)
    modelo: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    km: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")

    operacao: Mapped[Operacao] = relationship(back_populates="motos")
    contratos: Mapped[list[Contrato]] = relationship(back_populates="moto")
    lancamentos: Mapped[list[Financeiro]] = relationship(back_populates="moto")

    __table_args__ = (UniqueConstraint("operacao_id", "placa", name="uq_motos_operacao_placa"),)


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[str] = mapped_column(String(14), nullable=False)
    telefone: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    score: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="100")
    asaas_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    operacao: Mapped[Operacao] = relationship(back_populates="clientes")
    contratos: Mapped[list[Contrato]] = relationship(back_populates="cliente")

    __table_args__ = (UniqueConstraint("operacao_id", "cpf", name="uq_clientes_operacao_cpf"),)


class Contrato(Base):
    __tablename__ = "contratos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clientes.id"), nullable=False)
    moto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("motos.id"), nullable=False)
    valor_recorrente: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    ciclo: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim_vigencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    proximo_vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    nivel_escalonamento_cobranca: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    dias_atraso_acumulado: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    inadimplente: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    asaas_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asaas_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promessa_pagamento_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    promessa_notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    ultima_cobranca_telegram_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    mercadopago_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cliente: Mapped[Cliente] = relationship(back_populates="contratos")
    moto: Mapped[Moto] = relationship(back_populates="contratos")
    cobrancas: Mapped[list[Cobranca]] = relationship(back_populates="contrato")
    lancamentos: Mapped[list[Financeiro]] = relationship(back_populates="contrato")


class Financeiro(Base):
    __tablename__ = "financeiro"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    descricao: Mapped[str] = mapped_column(String(512), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    moto_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("motos.id"), nullable=True)
    contrato_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("contratos.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    moto: Mapped[Moto | None] = relationship(back_populates="lancamentos")
    contrato: Mapped[Contrato | None] = relationship(back_populates="lancamentos")


class Cobranca(Base):
    __tablename__ = "cobrancas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("operacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contrato_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("contratos.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    asaas_payment_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    mercadopago_payment_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    payment_gateway: Mapped[str] = mapped_column(String(32), nullable=False, server_default="asaas")
    pix_copia_cola: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contrato: Mapped[Contrato] = relationship(back_populates="cobrancas")


class EventoDominio(Base):
    __tablename__ = "eventos_dominio"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
