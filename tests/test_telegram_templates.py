from __future__ import annotations

import pytest
from motopay.domain.exceptions import ConflictError
from motopay.infrastructure.telegram.templates import (
    DEFAULT_TELEGRAM_TEMPLATES,
    build_overdue_html,
    merge_template_overrides,
    render_template,
    resolve_templates,
)


def test_resolve_templates_uses_defaults_when_no_overrides() -> None:
    resolved = resolve_templates(None)
    assert resolved == DEFAULT_TELEGRAM_TEMPLATES


def test_resolve_templates_merges_overrides() -> None:
    resolved = resolve_templates({"bot_start": "Olá customizado"})
    assert resolved["bot_start"] == "Olá customizado"
    assert resolved["bot_promessa_usage"] == DEFAULT_TELEGRAM_TEMPLATES["bot_promessa_usage"]


def test_merge_template_overrides_stores_only_diffs() -> None:
    stored = merge_template_overrides(None, {"bot_start": "Custom start"})
    assert stored == {"bot_start": "Custom start"}


def test_merge_template_overrides_removes_when_matches_default() -> None:
    default_start = DEFAULT_TELEGRAM_TEMPLATES["bot_start"]
    stored = merge_template_overrides({"bot_start": "Custom start"}, {"bot_start": default_start})
    assert stored is None


def test_merge_template_overrides_rejects_unknown_key() -> None:
    with pytest.raises(ConflictError, match="desconhecida"):
        merge_template_overrides(None, {"unknown_key": "x"})


def test_render_template_substitutes_placeholders() -> None:
    text = render_template(
        "moto_manutencao",
        overrides={"moto_manutencao": "Placa {placa} em manutenção."},
        placa="ABC1D23",
    )
    assert text == "Placa ABC1D23 em manutenção."


def test_build_overdue_html_includes_pix_and_escapes() -> None:
    payload = {
        "dias_atraso": 3,
        "valor_base": "350.00",
        "multa": "7.00",
        "juros": "1.05",
        "valor_total": "358.05",
        "pix_copia_cola": "PIX-TEST-CODE-123",
    }
    html = build_overdue_html(overrides=None, payload=payload, nivel=1)
    assert "PIX-TEST-CODE-123" in html
    assert "358,05" in html
    assert "<code>" in html
    assert DEFAULT_TELEGRAM_TEMPLATES["overdue_intro_1"] in html


def test_build_overdue_html_without_pix() -> None:
    payload = {
        "dias_atraso": 1,
        "valor_base": "100.00",
        "multa": "2.00",
        "juros": "0.10",
        "valor_total": "102.10",
        "pix_copia_cola": None,
    }
    html = build_overdue_html(overrides=None, payload=payload, nivel=0)
    assert DEFAULT_TELEGRAM_TEMPLATES["overdue_no_pix"] in html
