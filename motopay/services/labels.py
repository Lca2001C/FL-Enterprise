from __future__ import annotations

from motopay.domain.enums import ContratoStatus
from motopay.infrastructure.db.models import Cliente, Contrato, Moto


def moto_descricao(moto: Moto | None) -> str | None:
    """Descrição amigável da moto: "Modelo Ano Cor • PLACA" (ex.: "Start 2026 Azul • ABC1D23")."""
    if moto is None:
        return None
    parts = [moto.modelo]
    if moto.ano:
        parts.append(str(moto.ano))
    if moto.cor:
        parts.append(moto.cor)
    base = " ".join(p for p in parts if p)
    return f"{base} • {moto.placa}" if base else moto.placa


def _cliente_nome(cliente: Cliente | None) -> str | None:
    if cliente is None:
        return None
    nome = cliente.nome or ""
    if cliente.sobrenome:
        nome = f"{nome} {cliente.sobrenome}".strip()
    return nome or None


def locatario_nome(contrato: Contrato | None, moto: Moto | None) -> str | None:
    """Nome do locatário responsável.

    Prioriza o cliente do contrato vinculado (histórico); na ausência, usa o
    contrato ativo da moto (quem está com o veículo agora).
    """
    if contrato is not None and contrato.cliente is not None:
        return _cliente_nome(contrato.cliente)
    if moto is not None:
        active = next(
            (ct for ct in moto.contratos if ct.status == ContratoStatus.ATIVO.value), None
        )
        if active is not None:
            return _cliente_nome(active.cliente)
    return None
