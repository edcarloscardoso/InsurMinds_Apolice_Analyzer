"""Componentes de Cartões do InsurMinds — Insurance Intelligence v1.0.
Implementa Card institucional, MetricCard de KPIs e DifferenceCard para o confronto de cláusulas.
"""
from typing import Optional, List, Dict, Any
import streamlit as st
from ui.tokens import COLORS
from ui.components.badges import render_semantic_badge
from ui.styles import render_html


def render_card_start(
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    badge_html: Optional[str] = None,
    border_accent: Optional[str] = None
) -> None:
    """Renderiza a abertura de um cartão institucional corporativo com fundo branco e borda sutil."""
    accent_style = f"border-left: 4px solid {border_accent};" if border_accent else ""
    header_html = ""
    if title or badge_html:
        header_html = f"""
        <div class="im-card-header">
            <div>
                {f'<h4 class="im-card-title">{title}</h4>' if title else ''}
                {f'<p class="im-card-subtitle">{subtitle}</p>' if subtitle else ''}
            </div>
            {f'<div>{badge_html}</div>' if badge_html else ''}
        </div>
        """
    render_html(f"""
        <div class="im-card" style="{accent_style}">
            {header_html}
    """)


def render_card_end() -> None:
    """Fecha a tag do cartão institucional."""
    render_html("</div>")


def render_metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_type: str = "neutral",  # "positive", "negative", "neutral", "attention"
    help_text: Optional[str] = None
) -> None:
    """Renderiza um MetricCard corporativo sóbrio em HTML padronizado."""
    delta_colors = {
        "positive": COLORS.SUCCESS,
        "negative": COLORS.CRITICAL,
        "attention": COLORS.ATTENTION,
        "neutral": COLORS.TEXT_MUTED
    }
    delta_color = delta_colors.get(delta_type, COLORS.TEXT_MUTED)
    delta_html = f"<div class='im-metric-delta' style='color:{delta_color};'>{delta}</div>" if delta else ""
    help_attr = f"title='{help_text}'" if help_text else ""

    render_html(f"""
        <div class="im-metric-card" {help_attr}>
            <div class="im-metric-label">{label}</div>
            <div class="im-metric-value">{value}</div>
            {delta_html}
        </div>
    """)


def render_difference_card_html(
    relation: str,
    title_a: str,
    title_b: str,
    page_a: Optional[int],
    page_b: Optional[int],
    doc_a_name: str,
    doc_b_name: str,
    explanation: str,
    confidence_level: str = "Evidência forte"
) -> str:
    """Gera o HTML do DifferenceCard conforme o Design System Seção 8."""
    badge = render_semantic_badge(relation)
    page_a_str = f"Pág. {page_a}" if page_a else "Pág. não indicada"
    page_b_str = f"Pág. {page_b}" if page_b else "Pág. não indicada"

    # Borda esquerda com cor semântica discreta
    relation_colors = {
        "changed_scope": COLORS.ATTENTION,
        "changed_condition": "#7E22CE",
        "changed_limit": "#3730A3",
        "different": COLORS.CRITICAL,
        "broader": COLORS.SECONDARY_TEAL,
        "narrower": COLORS.PRIMARY_BLUE,
        "semantic_equivalent": COLORS.SUCCESS
    }
    border_color = relation_colors.get(relation, COLORS.BORDER)

    return f"""
    <div class="im-difference-card" style="border-left: 4px solid {border_color};">
        <div class="im-diff-header">
            <div>{badge}</div>
            <div class="im-diff-confidence">{confidence_level}</div>
        </div>
        <div class="im-diff-title">{title_a} &nbsp;⟷&nbsp; {title_b}</div>
        <div class="im-diff-pages">
            <span class="im-page-tag"><b>A ({doc_a_name}):</b> {page_a_str}</span>
            <span class="im-page-divider">·</span>
            <span class="im-page-tag"><b>B ({doc_b_name}):</b> {page_b_str}</span>
        </div>
        <div class="im-diff-explanation">
            <b>Interpretação assistida:</b> {explanation}
        </div>
    </div>
    """
