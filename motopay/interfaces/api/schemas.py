from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from motopay.domain.enums import (
    CicloCobranca,
    ContratoStatus,
    FinanceiroTipo,
    MotoStatus,
    PaymentProvider,
    UserRole,
)

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    tipo: UserRole
    operacao_id: int | None


class UserAdminOut(UserOut):
    created_at: datetime
    operacao_nome: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class OperacaoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)


class TelegramCustomMessage(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=80)
    trigger: str = Field(min_length=1, max_length=64)
    body: str = Field(min_length=1, max_length=2000)
    enabled: bool = True
    replace_default: bool = False


class CustomMessageTriggerMetaOut(BaseModel):
    trigger: str
    label: str
    description: str
    placeholders: list[str]


class OperacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    created_at: datetime
    multa_fixa_percentual: Decimal
    juros_diario_percentual: Decimal
    telegram_templates: dict[str, str] = Field(default_factory=dict)
    telegram_custom_messages: list[TelegramCustomMessage] = Field(default_factory=list)
    payment_provider: PaymentProvider = PaymentProvider.ASAAS


class OperacaoUpdate(BaseModel):
    nome: str | None = None
    multa_fixa_percentual: Decimal | None = None
    juros_diario_percentual: Decimal | None = None
    telegram_templates: dict[str, str | None] | None = None
    telegram_custom_messages: list[TelegramCustomMessage] | None = None
    payment_provider: PaymentProvider | None = None
    mercadopago_access_token: str | None = None


class TelegramTemplatePreviewRequest(BaseModel):
    key: str | None = None
    trigger: str | None = None
    template: str | None = None
    context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_key_or_trigger(self) -> TelegramTemplatePreviewRequest:
        if not self.key and not self.trigger:
            raise ValueError("Informe key ou trigger")
        if self.key and self.trigger:
            raise ValueError("Informe apenas key ou trigger")
        return self


class TelegramTemplatePreviewOut(BaseModel):
    text: str


class TelegramTemplateMetaOut(BaseModel):
    key: str
    label: str
    description: str
    placeholders: list[str]
    group: str
    default: str


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
    cliente_nome: str | None = None


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
    moto_placa: str | None = None
    moto_modelo: str | None = None


class ContratoCreate(BaseModel):
    cliente_id: int
    moto_id: int
    valor_recorrente: Decimal
    ciclo: CicloCobranca
    status: ContratoStatus = ContratoStatus.ATIVO
    data_inicio: date
    data_fim_vigencia: date | None = None
    proximo_vencimento: date

    @model_validator(mode="after")
    def validate_dates(self) -> ContratoCreate:
        if self.proximo_vencimento < self.data_inicio:
            raise ValueError("proximo_vencimento deve ser igual ou posterior a data_inicio")
        if self.data_fim_vigencia is not None and self.data_fim_vigencia < self.data_inicio:
            raise ValueError("data_fim_vigencia deve ser igual ou posterior a data_inicio")
        return self


class ContratoUpdate(BaseModel):
    status: ContratoStatus | None = None
    valor_recorrente: Decimal | None = None
    data_fim_vigencia: date | None = None
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
    data_fim_vigencia: date | None
    proximo_vencimento: date
    nivel_escalonamento_cobranca: int
    dias_atraso_acumulado: int
    inadimplente: bool
    promessa_pagamento_em: date | None
    promessa_notas: str | None
    asaas_subscription_id: str | None = None
    mercadopago_subscription_id: str | None = None


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
    id: int
    operacao_id: int
    contrato_id: int
    valor: Decimal
    vencimento: date
    asaas_payment_id: str | None
    mercadopago_payment_id: str | None = None
    payment_gateway: str = "asaas"
    pix_copia_cola: str | None
    status: str
    dias_atraso: int = 0
    multa: Decimal = Decimal(0)
    juros: Decimal = Decimal(0)
    valor_total: Decimal = Decimal(0)


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


class AnalyticsSummary(BaseModel):
    receita_total: Decimal
    despesa_total: Decimal
    lucro_liquido: Decimal
    motos_ativas: int
    clientes_inadimplentes: int
    total_cobrancas: int = 0
    cobrancas_pendentes: int = 0
    cobrancas_atrasadas: int = 0


class RecentActivityRow(BaseModel):
    id: int
    tipo: str
    descricao: str
    data: date
    valor: Decimal
