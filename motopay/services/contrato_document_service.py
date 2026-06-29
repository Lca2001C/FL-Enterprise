from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from motopay.config import app_today
from motopay.infrastructure.db.models import Cliente, Moto, Operacao
from motopay.interfaces.api.deps import CurrentUser
from motopay.services.fleet_service import get_contrato

CLAUSULAS = [
    (
        "1. Objeto",
        "O LOCADOR cede ao LOCATÁRIO o veículo descrito neste instrumento, exclusivamente "
        "para uso profissional/locativo, vedado empréstimo a terceiros ou uso diverso do acordado.",
    ),
    (
        "2. Pagamento",
        "O LOCATÁRIO pagará o valor recorrente indicado neste contrato, conforme ciclo "
        "de cobrança definido, na data de vencimento estipulada. Atrasos sujeitam-se às "
        "multas e juros configurados na operação.",
    ),
    (
        "3. Conservação",
        "O LOCATÁRIO responsabiliza-se pela guarda, conservação e manutenção preventiva do "
        "veículo, comunicando imediatamente ao LOCADOR qualquer sinistro, avaria ou furto.",
    ),
    (
        "4. Rescisão",
        "O contrato poderá ser encerrado conforme vigência acordada ou por descumprimento "
        "de obrigações. A devolução do veículo deve ocorrer nas condições registradas neste documento.",
    ),
]


def _brl(value: Decimal) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_date(value: date | None) -> str:
    if value is None:
        return "Indeterminado"
    return value.strftime("%d/%m/%Y")


def generate_contrato_pdf(
    db: Session,
    user: CurrentUser,
    operacao_scope: int | None,
    contrato_id: int,
) -> tuple[bytes, str]:
    ct = get_contrato(db, user, operacao_scope, contrato_id)
    cliente = db.get(Cliente, ct.cliente_id)
    moto = db.get(Moto, ct.moto_id)
    operacao = db.get(Operacao, ct.operacao_id)
    if not cliente or not moto or not operacao:
        from motopay.domain.exceptions import NotFoundError

        raise NotFoundError("Dados do contrato incompletos")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Contrato {ct.id}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1e293b"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#6366f1"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    )

    story: list = []
    story.append(Paragraph(operacao.nome, title_style))
    story.append(Paragraph("Contrato de Locação de Moto", subtitle_style))
    story.append(
        Paragraph(
            f"Documento nº {ct.id} · Emitido em {app_today().strftime('%d/%m/%Y')}",
            subtitle_style,
        )
    )

    parties_data = [
        ["LOCADOR", operacao.nome],
        ["LOCATÁRIO", f"{cliente.nome} · CPF {cliente.cpf}"],
        ["Contato", cliente.telefone],
    ]
    parties_table = Table(parties_data, colWidths=[4 * cm, 12 * cm])
    parties_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(parties_table)
    story.append(Spacer(1, 0.4 * cm))

    vehicle_data = [
        ["Placa", moto.placa, "Modelo", moto.modelo],
        ["Quilometragem", f"{moto.km:,} km".replace(",", "."), "Status veículo", moto.status],
    ]
    vehicle_table = Table(vehicle_data, colWidths=[3 * cm, 4 * cm, 3.5 * cm, 5.5 * cm])
    vehicle_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(Paragraph("Veículo locado", heading_style))
    story.append(vehicle_table)
    story.append(Spacer(1, 0.4 * cm))

    terms_data = [
        ["Valor recorrente", _brl(ct.valor_recorrente), "Ciclo", ct.ciclo],
        ["Início", _fmt_date(ct.data_inicio), "Fim da vigência", _fmt_date(ct.data_fim_vigencia)],
        ["Próximo vencimento", _fmt_date(ct.proximo_vencimento), "Status contrato", ct.status],
    ]
    terms_table = Table(terms_data, colWidths=[4 * cm, 4.5 * cm, 4 * cm, 3.5 * cm])
    terms_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef2ff")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(Paragraph("Condições financeiras", heading_style))
    story.append(terms_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Cláusulas gerais", heading_style))
    for titulo, texto in CLAUSULAS:
        story.append(Paragraph(f"<b>{titulo}</b>", body_style))
        story.append(Paragraph(texto, body_style))

    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "Assinaturas",
            ParagraphStyle(
                "Sign",
                parent=styles["Normal"],
                fontSize=11,
                alignment=TA_CENTER,
                spaceAfter=24,
            ),
        )
    )
    sign_data = [
        ["_" * 40, "_" * 40],
        ["LOCADOR", "LOCATÁRIO"],
    ]
    sign_table = Table(sign_data, colWidths=[8 * cm, 8 * cm])
    sign_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, 1), 8),
            ]
        )
    )
    story.append(sign_table)

    doc.build(story)
    filename = f"contrato-{ct.id}-{moto.placa.replace('-', '')}.pdf"
    return buffer.getvalue(), filename
