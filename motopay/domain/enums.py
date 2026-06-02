from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    DONO = "dono"


class MotoStatus(str, Enum):
    DISPONIVEL = "disponivel"
    ALUGADA = "alugada"
    MANUTENCAO = "manutencao"
    INATIVA = "inativa"


class ContratoStatus(str, Enum):
    ATIVO = "ativo"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"
    PENDENTE = "pendente"


class CicloCobranca(str, Enum):
    SEMANAL = "semanal"
    MENSAL = "mensal"


class FinanceiroTipo(str, Enum):
    RECEITA = "receita"
    DESPESA = "despesa"


class CobrancaStatus(str, Enum):
    PENDENTE = "pendente"
    RECEBIDO = "recebido"
    ATRASADO = "atrasado"
    CANCELADO = "cancelado"


class DomainEventType(str, Enum):
    PAGAMENTO_CONFIRMADO = "PAGAMENTO_CONFIRMADO"
    CLIENTE_INADIMPLENTE = "CLIENTE_INADIMPLENTE"
    MOTO_EM_MANUTENCAO = "MOTO_EM_MANUTENCAO"


class PaymentGateway(str, Enum):
    MERCADOPAGO = "mercadopago"


class PaymentMethodType(str, Enum):
    PIX = "pix"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
