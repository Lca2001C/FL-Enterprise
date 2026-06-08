from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from motopay.domain.exceptions import ConflictError
from motopay.infrastructure.db.models import Operacao

MAX_TEMPLATE_LENGTH = 2000
MAX_CUSTOM_MESSAGES = 10
MAX_BOT_MENU_BUTTONS = 6
MAX_BOT_MENU_LABEL_LENGTH = 32

BOT_MENU_BUILTIN_COMMANDS: frozenset[str] = frozenset({"status", "pix", "ajuda", "promessa", "menu"})
BOT_MENU_CUSTOM_COMMAND_RE = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
RESERVED_BOT_COMMANDS: frozenset[str] = frozenset({"start", *BOT_MENU_BUILTIN_COMMANDS})
MAX_BOT_MENU_RESPONSE_LENGTH = 2000

DEFAULT_BOT_MENU_CONTACT_BUTTON: dict[str, str] = {
    "label": "Quero falar com alguém",
    "command": "contato",
    "response": "Entendido, {cliente}. Nossa equipe entrará em contato em breve.",
}

DEFAULT_BOT_MENU_BUTTONS: list[dict[str, str]] = [
    {"label": "Status", "command": "status"},
    {"label": "Pix", "command": "pix"},
    {"label": "Ajuda", "command": "ajuda"},
    dict(DEFAULT_BOT_MENU_CONTACT_BUTTON),
]

DEFAULT_TELEGRAM_TEMPLATES: dict[str, str] = {
    "pagamento_confirmado": "✅ Pagamento confirmado! Obrigado. Sua locação segue em dia.",
    "overdue_intro_0": "Olá! Identificamos pendência no pagamento. Segue o Pix atualizado:",
    "overdue_intro_1": "⚠️ Atenção: seu pagamento está em atraso. Use o Pix abaixo:",
    "overdue_intro_2": "🔴 Cobrança firme: existe débito em aberto. Pix atualizado abaixo:",
    "overdue_body": (
        "Pagamento em atraso ({dias_atraso} dia(s))\n"
        "Aluguel: {valor_base}\n"
        "Multa: {multa}\n"
        "Juros: {juros}\n"
        "Total a pagar: {valor_total}"
    ),
    "overdue_pix_header": "Pix (copia e cola):",
    "overdue_pix_footer": "O Pix anterior foi cancelado; use apenas este código.",
    "overdue_no_pix": "Não foi possível gerar o Pix automaticamente. Fale com o operador.",
    "moto_manutencao": (
        "🔧 A moto {placa} entrou em manutenção. "
        "Entraremos em contato sobre prazos e substituição, se aplicável."
    ),
    "d3_reminder": (
        "Olá, {cliente}! 📅 Seu pagamento de R$ {valor_recorrente} vence em 3 dias "
        "({proximo_vencimento}). Fique tranquilo — pague até o vencimento e evite multa e juros."
    ),
    "d1_reminder": (
        "Lembrete: amanhã ({proximo_vencimento}) vence o pagamento "
        "do contrato #{contrato_id} no valor de R$ {valor_recorrente}."
    ),
    "d0_reminder": (
        "Hoje ({proximo_vencimento}) vence o pagamento do contrato #{contrato_id} "
        "no valor de R$ {valor_recorrente}. Realize o pagamento para evitar multa."
    ),
    "bot_start": (
        "Olá, {cliente}!\n\n"
        "Próximo vencimento: {proximo_vencimento}\n"
        "Placa: {placa}\n"
        "Inadimplente: {inadimplente}\n"
        "Promessa: {promessa_pagamento_em}\n\n"
        "Use os botões abaixo, /menu ou /promessa <dias> <motivo>."
    ),
    "bot_promessa_usage": "Uso: /promessa 3 pagar na próxima sexta-feira",
    "bot_promessa_invalid_days": "Informe um número válido de dias.",
    "bot_promessa_no_user": "Não foi possível identificar seu usuário no Telegram.",
    "bot_promessa_error": "Erro ao registrar. Tente novamente ou fale com o operador.",
    "bot_promessa_success": "Registramos sua promessa. Obrigado pelo retorno.",
    "bot_promessa_not_found": (
        "Não localizamos seu cadastro com este Telegram. Peça ao operador para informar seu ID."
    ),
    "bot_pix": "Pix pendente — vencimento {vencimento}\n{valor_detalhado}\n\n{pix_copia_cola}",
    "bot_pix_portal": (
        "Pagamento pendente — vencimento {vencimento}\n{valor_detalhado}\n\n"
        "Pague online: {portal_url}\n\n{pix_block}"
    ),
    "estorno_confirmado": (
        "Confirmamos o estorno de R$ {delta} referente à cobrança #{cobranca_id}. "
        "O valor pode levar alguns dias para aparecer na fatura."
    ),
    "overdue_portal_link": "Pague online pelo link: {portal_url}",
    "bot_status": (
        "Contrato: vencimento {proximo_vencimento}. Inadimplente: {inadimplente}. "
        "Promessa: {promessa_pagamento_em}."
    ),
    "bot_ajuda": (
        "Comandos: /menu /pix /status /promessa <dias> <motivo>. "
        "Dúvidas? Fale com o operador."
    ),
    "bot_comando_desconhecido": (
        "Comando /{comando} não reconhecido. Use /menu para ver as opções."
    ),
    "bot_chat_greeting": (
        "Olá, {cliente}! Tudo bem?\n"
        "Se precisar de Pix, status ou registrar uma promessa, use os botões abaixo."
    ),
    "bot_chat_ack": (
        "Recebemos sua mensagem, {cliente}. Nossa equipe já foi avisada e entraremos em contato em breve."
    ),
    "bot_chat_thanks": "Por nada, {cliente}! Qualquer coisa, estamos à disposição.",
    "bot_chat_contact": (
        "Entendido, {cliente}. Já repassamos para a equipe — entraremos em contato em breve."
    ),
    "bot_chat_payment": (
        "Sobre pagamento: toque em Pix ou Status nos botões abaixo, ou envie "
        "/promessa <dias> <motivo> se precisar combinar uma data."
    ),
}


@dataclass(frozen=True)
class TelegramTemplateMeta:
    key: str
    label: str
    description: str
    placeholders: tuple[str, ...]
    group: str


TELEGRAM_TEMPLATE_META: dict[str, TelegramTemplateMeta] = {
    "pagamento_confirmado": TelegramTemplateMeta(
        key="pagamento_confirmado",
        label="Pagamento confirmado",
        description="Enviada quando um pagamento é confirmado via webhook Mercado Pago.",
        placeholders=(),
        group="notificacoes",
    ),
    "overdue_intro_0": TelegramTemplateMeta(
        key="overdue_intro_0",
        label="Inadimplência — tom suave (nível 0)",
        description="Primeira linha da cobrança por atraso (até 2 dias).",
        placeholders=(),
        group="notificacoes",
    ),
    "overdue_intro_1": TelegramTemplateMeta(
        key="overdue_intro_1",
        label="Inadimplência — tom médio (nível 1)",
        description="Primeira linha da cobrança (3 a 6 dias de atraso).",
        placeholders=(),
        group="notificacoes",
    ),
    "overdue_intro_2": TelegramTemplateMeta(
        key="overdue_intro_2",
        label="Inadimplência — tom firme (nível 2)",
        description="Primeira linha da cobrança (7+ dias de atraso).",
        placeholders=(),
        group="notificacoes",
    ),
    "overdue_body": TelegramTemplateMeta(
        key="overdue_body",
        label="Inadimplência — corpo",
        description="Detalhes do débito (valores já formatados em reais).",
        placeholders=("dias_atraso", "valor_base", "multa", "juros", "valor_total"),
        group="notificacoes",
    ),
    "overdue_pix_header": TelegramTemplateMeta(
        key="overdue_pix_header",
        label="Inadimplência — rótulo Pix",
        description="Texto antes do código Pix copia e cola.",
        placeholders=(),
        group="notificacoes",
    ),
    "overdue_pix_footer": TelegramTemplateMeta(
        key="overdue_pix_footer",
        label="Inadimplência — rodapé Pix",
        description="Texto após o código Pix.",
        placeholders=(),
        group="notificacoes",
    ),
    "overdue_no_pix": TelegramTemplateMeta(
        key="overdue_no_pix",
        label="Inadimplência — sem Pix",
        description="Quando não foi possível gerar o Pix automaticamente.",
        placeholders=(),
        group="notificacoes",
    ),
    "moto_manutencao": TelegramTemplateMeta(
        key="moto_manutencao",
        label="Moto em manutenção",
        description="Aviso ao locatário quando a moto entra em manutenção.",
        placeholders=("placa",),
        group="notificacoes",
    ),
    "d3_reminder": TelegramTemplateMeta(
        key="d3_reminder",
        label="Lembrete D-3",
        description="Lembrete enviado três dias antes do vencimento.",
        placeholders=("cliente", "proximo_vencimento", "valor_recorrente"),
        group="notificacoes",
    ),
    "d1_reminder": TelegramTemplateMeta(
        key="d1_reminder",
        label="Lembrete D-1",
        description="Lembrete enviado um dia antes do vencimento.",
        placeholders=("proximo_vencimento", "contrato_id", "valor_recorrente"),
        group="notificacoes",
    ),
    "d0_reminder": TelegramTemplateMeta(
        key="d0_reminder",
        label="Lembrete D-0",
        description="Lembrete no dia do vencimento.",
        placeholders=("proximo_vencimento", "contrato_id", "valor_recorrente"),
        group="notificacoes",
    ),
    "bot_pix": TelegramTemplateMeta(
        key="bot_pix",
        label="Bot — /pix",
        description="Resposta com Pix pendente.",
        placeholders=("valor_detalhado", "valor_total", "pix_copia_cola", "vencimento"),
        group="bot",
    ),
    "bot_status": TelegramTemplateMeta(
        key="bot_status",
        label="Bot — /status",
        description="Resumo do contrato.",
        placeholders=("proximo_vencimento", "inadimplente", "promessa_pagamento_em"),
        group="bot",
    ),
    "bot_ajuda": TelegramTemplateMeta(
        key="bot_ajuda",
        label="Bot — /ajuda",
        description="Resposta fixa quando IA desligada.",
        placeholders=(),
        group="bot",
    ),
    "bot_comando_desconhecido": TelegramTemplateMeta(
        key="bot_comando_desconhecido",
        label="Bot — comando desconhecido",
        description="Quando o cliente envia um /comando que não existe.",
        placeholders=("comando",),
        group="bot",
    ),
    "bot_chat_greeting": TelegramTemplateMeta(
        key="bot_chat_greeting",
        label="Bot — saudação",
        description="Resposta a oi/olá sem reenviar o menu completo.",
        placeholders=("cliente",),
        group="bot",
    ),
    "bot_chat_ack": TelegramTemplateMeta(
        key="bot_chat_ack",
        label="Bot — mensagem geral",
        description="Resposta padrão a textos livres (não reenvia o menu).",
        placeholders=("cliente",),
        group="bot",
    ),
    "bot_chat_thanks": TelegramTemplateMeta(
        key="bot_chat_thanks",
        label="Bot — agradecimento",
        description="Resposta quando o cliente agradece.",
        placeholders=("cliente",),
        group="bot",
    ),
    "bot_chat_contact": TelegramTemplateMeta(
        key="bot_chat_contact",
        label="Bot — pedido de contato",
        description="Quando pedem atendente, ligação ou retorno.",
        placeholders=("cliente",),
        group="bot",
    ),
    "bot_chat_payment": TelegramTemplateMeta(
        key="bot_chat_payment",
        label="Bot — dúvida de pagamento",
        description="Quando mencionam Pix, pagamento ou atraso.",
        placeholders=("cliente",),
        group="bot",
    ),
    "bot_start": TelegramTemplateMeta(
        key="bot_start",
        label="Bot — menu principal",
        description="Texto exibido no /start e ao receber mensagens livres no bot.",
        placeholders=(
            "cliente",
            "proximo_vencimento",
            "placa",
            "inadimplente",
            "promessa_pagamento_em",
        ),
        group="bot",
    ),
    "bot_promessa_usage": TelegramTemplateMeta(
        key="bot_promessa_usage",
        label="Bot — uso de /promessa",
        description="Quando o comando /promessa é usado incorretamente.",
        placeholders=(),
        group="bot",
    ),
    "bot_promessa_invalid_days": TelegramTemplateMeta(
        key="bot_promessa_invalid_days",
        label="Bot — dias inválidos",
        description="Quando o número de dias em /promessa não é válido.",
        placeholders=(),
        group="bot",
    ),
    "bot_promessa_no_user": TelegramTemplateMeta(
        key="bot_promessa_no_user",
        label="Bot — usuário não identificado",
        description="Quando o Telegram não informa o ID do usuário.",
        placeholders=(),
        group="bot",
    ),
    "bot_promessa_error": TelegramTemplateMeta(
        key="bot_promessa_error",
        label="Bot — erro ao registrar",
        description="Erro inesperado ao salvar a promessa.",
        placeholders=(),
        group="bot",
    ),
    "bot_promessa_success": TelegramTemplateMeta(
        key="bot_promessa_success",
        label="Bot — promessa registrada",
        description="Confirmação após registrar promessa de pagamento.",
        placeholders=(),
        group="bot",
    ),
    "bot_promessa_not_found": TelegramTemplateMeta(
        key="bot_promessa_not_found",
        label="Bot — cadastro não encontrado",
        description="Quando o Telegram não está vinculado a nenhum cliente.",
        placeholders=(),
        group="bot",
    ),
}


CUSTOM_MESSAGE_TRIGGER_KEYS: frozenset[str] = frozenset(
    {"pagamento_confirmado", "d3_reminder", "d1_reminder", "d0_reminder", "moto_manutencao"}
)


class _SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def resolve_templates(overrides: dict[str, str] | None) -> dict[str, str]:
    merged = dict(DEFAULT_TELEGRAM_TEMPLATES)
    if overrides:
        for key, value in overrides.items():
            if key in merged and value is not None:
                merged[key] = value
    return merged


def _validate_template_key(key: str) -> None:
    if key not in TELEGRAM_TEMPLATE_META:
        raise ConflictError(f"Chave de template desconhecida: {key}")


def _validate_template_value(key: str, value: str) -> None:
    if len(value) > MAX_TEMPLATE_LENGTH:
        raise ConflictError(f"Template '{key}' excede {MAX_TEMPLATE_LENGTH} caracteres")


def merge_template_overrides(
    existing: dict[str, str] | None,
    updates: dict[str, str | None] | None,
) -> dict[str, str] | None:
    if updates is None:
        return existing
    stored = dict(existing or {})
    for key, value in updates.items():
        _validate_template_key(key)
        if value is None or value.strip() == "":
            stored.pop(key, None)
            continue
        _validate_template_value(key, value)
        if value == DEFAULT_TELEGRAM_TEMPLATES[key]:
            stored.pop(key, None)
        else:
            stored[key] = value
    return stored or None


def render_template(
    key: str,
    *,
    overrides: dict[str, str] | None = None,
    templates: dict[str, str] | None = None,
    escape_html: bool = False,
    **context: Any,
) -> str:
    resolved = templates or resolve_templates(overrides)
    if key not in resolved:
        raise KeyError(key)
    template = resolved[key]
    safe_ctx: dict[str, str] = {}
    for name, raw in context.items():
        text = str(raw)
        safe_ctx[name] = html.escape(text) if escape_html else text
    return template.format_map(_SafeFormatDict(safe_ctx))


def format_brl(value: Decimal | float) -> str:
    return f"R$ {Decimal(value):.2f}".replace(".", ",")


def build_overdue_html(
    *,
    overrides: dict[str, str] | None,
    payload: dict,
    nivel: int,
) -> str:
    templates = resolve_templates(overrides)
    intro_key = f"overdue_intro_{min(nivel, 2)}"
    dias = int(payload.get("dias_atraso", 0))
    valor_base = Decimal(str(payload.get("valor_base", 0)))
    multa = Decimal(str(payload.get("multa", 0)))
    juros = Decimal(str(payload.get("juros", 0)))
    valor_total = Decimal(str(payload.get("valor_total", 0)))
    pix = payload.get("pix_copia_cola") or ""
    portal_url = payload.get("portal_url") or ""

    intro = html.escape(templates[intro_key])
    body = render_template(
        "overdue_body",
        templates=templates,
        escape_html=True,
        dias_atraso=dias,
        valor_base=format_brl(valor_base),
        multa=format_brl(multa),
        juros=format_brl(juros),
        valor_total=format_brl(valor_total),
    )

    lines = [intro, ""] + body.split("\n")
    if portal_url:
        portal_line = render_template(
            "overdue_portal_link",
            templates=templates,
            escape_html=True,
            portal_url=portal_url,
        )
        lines.extend(["", portal_line])
    if pix:
        lines.extend(
            [
                "",
                html.escape(templates["overdue_pix_header"]),
                f"<code>{html.escape(str(pix))}</code>",
                "",
                html.escape(templates["overdue_pix_footer"]),
            ]
        )
    else:
        lines.extend(["", html.escape(templates["overdue_no_pix"])])
    return "\n".join(lines)


def list_template_meta() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for meta in TELEGRAM_TEMPLATE_META.values():
        rows.append(
            {
                "key": meta.key,
                "label": meta.label,
                "description": meta.description,
                "placeholders": list(meta.placeholders),
                "group": meta.group,
                "default": DEFAULT_TELEGRAM_TEMPLATES[meta.key],
            }
        )
    return rows


def sample_context_for_key(key: str) -> dict[str, Any]:
    """Contexto de exemplo para pré-visualização no admin."""
    from datetime import date

    today = date.today()
    samples: dict[str, dict[str, Any]] = {
        "overdue_intro_0": {},
        "overdue_body": {
            "dias_atraso": 3,
            "valor_base": "350,00",
            "multa": "7,00",
            "juros": "1,05",
            "valor_total": "358,05",
        },
        "d3_reminder": {
            "cliente": "João Silva",
            "proximo_vencimento": today.isoformat(),
            "valor_recorrente": "350,00",
        },
        "d1_reminder": {
            "proximo_vencimento": today.isoformat(),
            "contrato_id": 42,
            "valor_recorrente": "350.00",
        },
        "d0_reminder": {
            "proximo_vencimento": today.isoformat(),
            "contrato_id": 42,
            "valor_recorrente": "350.00",
        },
        "moto_manutencao": {"placa": "ABC1D23"},
        "bot_pix": {
            "vencimento": today.isoformat(),
            "valor_detalhado": "Total: R$ 350,00",
            "valor_total": "R$ 350,00",
            "pix_copia_cola": "000201010212...",
        },
        "bot_status": {
            "proximo_vencimento": today.isoformat(),
            "inadimplente": "sim",
            "promessa_pagamento_em": "—",
        },
        "bot_start": {
            "cliente": "João Silva",
            "proximo_vencimento": today.isoformat(),
            "placa": "ABC1D23",
            "inadimplente": "não",
            "promessa_pagamento_em": "—",
        },
        "bot_chat_greeting": {"cliente": "João Silva"},
        "bot_chat_ack": {"cliente": "João Silva"},
        "bot_chat_thanks": {"cliente": "João Silva"},
        "bot_chat_contact": {"cliente": "João Silva"},
        "bot_chat_payment": {"cliente": "João Silva"},
        "bot_comando_desconhecido": {"comando": "exemplo"},
    }
    meta = TELEGRAM_TEMPLATE_META.get(key)
    ctx = samples.get(key, {})
    if meta:
        for ph in meta.placeholders:
            ctx.setdefault(ph, f"[{ph}]")
    return ctx


def list_custom_message_triggers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(CUSTOM_MESSAGE_TRIGGER_KEYS):
        meta = TELEGRAM_TEMPLATE_META[key]
        rows.append(
            {
                "trigger": meta.key,
                "label": meta.label,
                "description": meta.description,
                "placeholders": list(meta.placeholders),
            }
        )
    return rows


def resolve_bot_menu_buttons(buttons: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if not buttons:
        return [dict(b) for b in DEFAULT_BOT_MENU_BUTTONS]
    return validate_bot_menu_buttons(buttons)


def validate_bot_menu_buttons(buttons: list[dict[str, Any]]) -> list[dict[str, str]]:
    if len(buttons) > MAX_BOT_MENU_BUTTONS:
        raise ConflictError(f"Máximo de {MAX_BOT_MENU_BUTTONS} botões no menu")
    if len(buttons) < 1:
        raise ConflictError("O menu precisa de pelo menos um botão")
    seen_labels: set[str] = set()
    seen_commands: set[str] = set()
    normalized: list[dict[str, str]] = []
    menu_ctx = sample_context_for_key("bot_start")
    for btn in buttons:
        label = str(btn.get("label", "")).strip()
        command = str(btn.get("command", "")).strip().lower()
        response_raw = btn.get("response")
        response = str(response_raw).strip() if response_raw is not None else ""
        if not label or len(label) > MAX_BOT_MENU_LABEL_LENGTH:
            raise ConflictError(
                f"Label do botão deve ter entre 1 e {MAX_BOT_MENU_LABEL_LENGTH} caracteres"
            )
        if label in seen_labels:
            raise ConflictError(f"Label duplicado no menu: {label}")
        if command in seen_commands:
            raise ConflictError(f"Comando duplicado no menu: {command}")
        if command in BOT_MENU_BUILTIN_COMMANDS:
            if response:
                raise ConflictError(
                    f"Comando integrado '{command}' não aceita texto personalizado"
                )
            seen_labels.add(label)
            seen_commands.add(command)
            normalized.append({"label": label, "command": command})
            continue
        if command in RESERVED_BOT_COMMANDS:
            raise ConflictError(f"Comando reservado: {command}")
        if not BOT_MENU_CUSTOM_COMMAND_RE.match(command):
            raise ConflictError(
                "Comando personalizado inválido (use letras minúsculas, números e _)"
            )
        if not response:
            raise ConflictError(f"Comando personalizado '{command}' precisa de uma resposta")
        if len(response) > MAX_BOT_MENU_RESPONSE_LENGTH:
            raise ConflictError(
                f"Resposta do comando excede {MAX_BOT_MENU_RESPONSE_LENGTH} caracteres"
            )
        try:
            render_custom_body(response, **menu_ctx)
        except (KeyError, ValueError) as e:
            raise ConflictError(f"Resposta inválida para '{command}': {e}") from e
        seen_labels.add(label)
        seen_commands.add(command)
        normalized.append({"label": label, "command": command, "response": response})
    return normalized


def match_button_command(text: str, buttons: list[dict[str, str]]) -> str | None:
    stripped = text.strip()
    for btn in buttons:
        if stripped == btn["label"]:
            return btn["command"]
    return None


def find_menu_button_by_command(command: str, buttons: list[dict[str, str]]) -> dict[str, str] | None:
    cmd = command.strip().lower()
    for btn in buttons:
        if btn["command"] == cmd:
            return btn
    return None


def render_menu_button_response(button: dict[str, str], *, menu_ctx: dict[str, str]) -> str:
    response = button.get("response")
    if not response:
        return ""
    return render_custom_body(response, **menu_ctx)


def validate_custom_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(messages) > MAX_CUSTOM_MESSAGES:
        raise ConflictError(f"Máximo de {MAX_CUSTOM_MESSAGES} mensagens personalizadas")
    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for msg in messages:
        msg_id = str(msg.get("id", "")).strip()
        label = str(msg.get("label", "")).strip()
        trigger = str(msg.get("trigger", "")).strip()
        body = str(msg.get("body", "")).strip()
        if not msg_id or msg_id in seen_ids:
            raise ConflictError("Cada mensagem personalizada precisa de id único")
        if trigger not in CUSTOM_MESSAGE_TRIGGER_KEYS:
            raise ConflictError(f"Gatilho inválido: {trigger}")
        if not label:
            raise ConflictError("Nome da mensagem é obrigatório")
        if not body:
            raise ConflictError("Texto da mensagem é obrigatório")
        if len(body) > MAX_TEMPLATE_LENGTH:
            raise ConflictError(f"Mensagem excede {MAX_TEMPLATE_LENGTH} caracteres")
        seen_ids.add(msg_id)
        enabled = bool(msg.get("enabled", True))
        replace_default = bool(msg.get("replace_default", False))
        try:
            render_custom_body(body, **sample_context_for_key(trigger))
        except (KeyError, ValueError) as e:
            raise ConflictError(f"Texto inválido para gatilho '{trigger}': {e}") from e
        normalized.append(
            {
                "id": msg_id,
                "label": label,
                "trigger": trigger,
                "body": body,
                "enabled": enabled,
                "replace_default": replace_default,
            }
        )
    return normalized


def render_custom_body(body: str, **context: Any) -> str:
    safe_ctx: dict[str, str] = {name: str(raw) for name, raw in context.items()}
    return body.format_map(_SafeFormatDict(safe_ctx))


def custom_messages_for_trigger(
    operacao: Operacao | None, trigger: str
) -> list[dict[str, Any]]:
    if operacao is None:
        return []
    raw = operacao.telegram_custom_messages or []
    return [m for m in raw if m.get("trigger") == trigger and m.get("enabled", True)]


def should_skip_default_template(operacao: Operacao | None, trigger: str) -> bool:
    return any(m.get("replace_default") for m in custom_messages_for_trigger(operacao, trigger))


def render_custom_messages_for_trigger(
    operacao: Operacao | None, trigger: str, **context: Any
) -> list[str]:
    return [
        render_custom_body(str(m["body"]), **context)
        for m in custom_messages_for_trigger(operacao, trigger)
    ]
