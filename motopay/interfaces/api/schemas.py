from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from motopay.domain.enums import CicloCobranca, ContratoStatus, FinanceiroTipo, MotoStatus, UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    tipo: UserRole
    operacao_id: int | None


class OperacaoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)


class OperacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    created_at: datetime


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tipo: UserRole
    operacao_id: int | None = None


class MotoCreate(BaseModel):
    placa: str
    modelo: str
    status: MotoStatus


class MotoUpdate(BaseModel):
    placa: str | None = None
    modelo: str | None = None
    status: MotoStatus | None = None


class MotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao_id: int
    placa: str
    modelo: str
    status: str


class ClienteCreate(BaseModel):
    nome: str
    cpf: str
    telefone: str
    telegram_id: str | None = None


class ClienteUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    telegram_id: str | None = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao_id: int
    nome: str
    cpf: str
    telefone: str
    telegram_id: str | None
    score: int


class ContratoCreate(BaseModel):
    cliente_id: int
    moto_id: int
    valor_recorrente: Decimal
    ciclo: CicloCobranca
    status: ContratoStatus = ContratoStatus.ATIVO
    data_inicio: date
    proximo_vencimento: date


class ContratoUpdate(BaseModel):
    status: ContratoStatus | None = None
    valor_recorrente: Decimal | None = None
    proximo_vencimento: date | None = None


class ContratoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao_id: int
    cliente_id: int
    moto_id: int
    valor_recorrente: Decimal
    ciclo: str
    status: str
    data_inicio: date
    proximo_vencimento: date
    nivel_escalonamento_cobranca: int
    dias_atraso_acumulado: int
    inadimplente: bool
    promessa_pagamento_em: date | None
    promessa_notas: str | None
    asaas_subscription_id: str | None = None


class FinanceiroCreate(BaseModel):
    tipo: FinanceiroTipo
    valor: Decimal
    descricao: str
    data: date
    moto_id: int | None = None
    contrato_id: int | None = None


class FinanceiroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao_id: int
    tipo: str
    valor: Decimal
    descricao: str
    data: date
    moto_id: int | None
    contrato_id: int | None


class CobrancaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao_id: int
    contrato_id: int
    valor: Decimal
    vencimento: date
    asaas_payment_id: str | None
    pix_copia_cola: str | None
    status: str


class CreateChargeRequest(BaseModel):
    contrato_id: int
    """Cria cobrança avulsa via Asaas quando configurado."""


class MotoAnalyticsRow(BaseModel):
    moto_id: int
    placa: str
    modelo: str
    receita: Decimal
    despesa: Decimal
    lucro_liquido: Decimal
    roi: Decimal | None
    prejuizo: bool


class WebhookAsaasPayload(BaseModel):
    event: str
    payment: dict[str, Any] | None = None
