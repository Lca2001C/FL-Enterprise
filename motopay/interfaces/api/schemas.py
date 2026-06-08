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
    UserRole,
    VeiculoTipo,
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
    # str (não EmailStr) para aceitar domínios locais/de teste como .local
    # max_length evita chaves Redis gigantes no rate-limit
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=256)


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


class TelegramBotMenuButton(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    command: str = Field(min_length=1, max_length=32)
    response: str | None = Field(default=None, max_length=2000)


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
    telegram_bot_menu_buttons: list[TelegramBotMenuButton] = Field(default_factory=list)
    telegram_owner_notify_id: str | None = None
    telegram_owner_notify_enabled: bool = False


class OperacaoUpdate(BaseModel):
    nome: str | None = None
    multa_fixa_percentual: Decimal | None = None
    juros_diario_percentual: Decimal | None = None
    telegram_templates: dict[str, str | None] | None = None
    telegram_custom_messages: list[TelegramCustomMessage] | None = None
    telegram_bot_menu_buttons: list[TelegramBotMenuButton] | None = None
    telegram_owner_notify_id: str | None = None
    telegram_owner_notify_enabled: bool | None = None
    mercadopago_access_token: str | None = None
    mercadopago_public_key: str | None = None
    mercadopago_webhook_secret: str | None = None


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
    tipo: VeiculoTipo = VeiculoTipo.MOTO
    status: MotoStatus
    km: int = 0


class MotoUpdate(BaseModel):
    placa: str | None = None
    modelo: str | None = None
    tipo: VeiculoTipo | None = None
    status: MotoStatus | None = None
    km: int | None = None


class MotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao_id: int
    placa: str
    modelo: str
    tipo: str = "moto"
    status: str
    km: int
    tem_imagem: bool = False
    cliente_nome: str | None = None


class ClienteCreate(BaseModel):
    nome: str
    sobrenome: str | None = None
    cpf: str
    telefone: str
    email: str | None = None
    telegram_id: str | None = None
    endereco_logradouro: str | None = None
    endereco_numero: str | None = None
    endereco_bairro: str | None = None
    endereco_cidade: str | None = None
    endereco_estado: str | None = None
    endereco_cep: str | None = None


class ClienteUpdate(BaseModel):
    nome: str | None = None
    sobrenome: str | None = None
    telefone: str | None = None
    email: str | None = None
    telegram_id: str | None = None
    endereco_logradouro: str | None = None
    endereco_numero: str | None = None
    endereco_bairro: str | None = None
    endereco_cidade: str | None = None
    endereco_estado: str | None = None
    endereco_cep: str | None = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operacao_id: int
    nome: str
    sobrenome: str | None = None
    cpf: str
    telefone: str
    email: str | None = None
    mercadopago_customer_id: str | None = None
    telegram_id: str | None
    score: int
    moto_placa: str | None = None
    moto_modelo: str | None = None
    endereco_logradouro: str | None = None
    endereco_numero: str | None = None
    endereco_bairro: str | None = None
    endereco_cidade: str | None = None
    endereco_estado: str | None = None
    endereco_cep: str | None = None


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
    ciclo: CicloCobranca | None = None
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
    mercadopago_subscription_id: str | None = None
    mercadopago_subscription_status: str | None = None


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
    mercadopago_payment_id: str | None = None
    mercadopago_order_id: str | None = None
    payment_gateway: str = "mercadopago"
    payment_method_type: str | None = None
    pix_copia_cola: str | None
    status: str
    dias_atraso: int = 0
    multa: Decimal = Decimal(0)
    juros: Decimal = Decimal(0)
    valor_total: Decimal = Decimal(0)
    valor_estornado: Decimal = Decimal(0)
    mercadopago_dispute_status: str | None = None
    mercadopago_payment_status: str | None = None


class CreateChargeRequest(BaseModel):
    contrato_id: int
    """Cria cobrança Pix via Mercado Pago quando configurado."""


class MotoAnalyticsRow(BaseModel):
    moto_id: int
    placa: str
    modelo: str
    receita: Decimal
    despesa: Decimal
    lucro_liquido: Decimal
    roi: Decimal | None
    prejuizo: bool


class AnalyticsSummary(BaseModel):
    receita_total: Decimal
    despesa_total: Decimal
    lucro_liquido: Decimal
    motos_ativas: int
    clientes_inadimplentes: int
    total_cobrancas: int = 0
    cobrancas_pendentes: int = 0
    cobrancas_atrasadas: int = 0


class DashboardInadimplenciaItem(BaseModel):
    contrato_id: int
    cliente_nome: str
    dias_atraso: int
    proximo_vencimento: date
    pix_copia_cola: str | None = None


class RecentActivityRow(BaseModel):
    id: int
    tipo: str
    descricao: str
    data: date
    valor: Decimal


class PaymentsConfigOut(BaseModel):
    mercadopago_configured: bool
    mercadopago_public_key: str | None = None
    webhook_configured: bool
    credentials_mode: str = "production"
    mercadopago_credentials_source: str = "none"
    mercadopago_credentials_complete: bool = False
    mercadopago_has_operacao_token: bool = False
    mercadopago_oauth_available: bool = False
    mercadopago_oauth_connected: bool = False
    mercadopago_webhook_ready: bool = False
    webhook_url: str | None = None


class ClienteMpCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    operacao_id: int
    mp_card_id: str
    payment_method_id: str
    last_four_digits: str
    cardholder_name: str | None = None
    expiration_month: int | None = None
    expiration_year: int | None = None
    is_default: bool = False


class SaveMpCardRequest(BaseModel):
    token: str = Field(min_length=1)


class CardPaymentRequest(BaseModel):
    token: str = Field(min_length=1)
    payment_method_id: str = Field(min_length=1)
    payment_method_kind: str = "credit_card"
    saved_card_id: int | None = None
    installments: int = 1
    device_id: str | None = None


class ThreeDsInfoOut(BaseModel):
    external_resource_url: str | None = None
    creq: str | None = None


class CardPaymentOut(BaseModel):
    cobranca: CobrancaOut
    order_id: str
    payment_id: str
    status: str
    requires_3ds: bool = False
    three_ds_info: ThreeDsInfoOut | None = None


class MpSubscriptionOut(BaseModel):
    contrato_id: int
    mercadopago_subscription_id: str
    init_point: str | None = None
    status: str | None = None


class PortalLinkOut(BaseModel):
    token: str
    url: str


class PayerPortalOut(BaseModel):
    cobranca: CobrancaOut
    cliente_nome: str
    cliente_id: int
    cliente_email: str | None = None
    cliente_cpf: str
    mercadopago_public_key: str | None = None
    credentials_mode: str = "production"
    payable: bool = True


class PortalCardPaymentRequest(BaseModel):
    token: str = Field(min_length=1)
    payment_method_id: str = Field(min_length=1)
    payment_method_kind: str = "credit_card"
    saved_card_id: int | None = None
    installments: int = 1
    device_id: str | None = None


class RefundRequest(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)


class MpOAuthStartOut(BaseModel):
    authorization_url: str
    redirect_uri: str
