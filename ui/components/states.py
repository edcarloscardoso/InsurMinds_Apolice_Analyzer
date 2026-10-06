"""Componentes de Estados Visuais e Alertas — Insurance Intelligence v1.0.
Padroniza os estados Empty, Loading, Success, Partial, Error, Fallback e Alertas Corporativos.
"""
from typing import Optional, Callable
import streamlit as st
from ui.tokens import COLORS
from ui.styles import render_html


def render_empty_state(
    title: str = "Não há análises disponíveis.",
    description: str = "Inicie uma nova análise carregando dois contratos PDF ou escolha um par de teste do repositório.",
    action_label: Optional[str] = None,
    action_callback: Optional[Callable] = None
) -> None:
    """Renderiza um EmptyState institucional limpo e convidativo."""
    render_html(f"""
        <div class="im-state-box im-empty-state">
            <div class="im-state-icon">📋</div>
            <h4 class="im-state-title">{title}</h4>
            <p class="im-state-desc">{description}</p>
        </div>
    """)
    if action_label and action_callback:
        col_c, _ = st.columns([1.5, 3])
        with col_c:
            st.button(action_label, type="primary", on_click=action_callback, key="btn_empty_action")


def render_loading_state(message: str = "Processando documentos...") -> None:
    """Renderiza um LoadingState discreto e sem efeitos exagerados."""
    render_html(f"""
        <div class="im-state-box im-loading-state">
            <div class="im-spinner"></div>
            <div class="im-state-text"><b>{message}</b></div>
        </div>
    """)


def render_success_state(
    title: str = "Análise concluída.",
    message: Optional[str] = None
) -> None:
    """Renderiza um SuccessState corporativo confirmado."""
    msg_html = f"<p class='im-state-desc'>{message}</p>" if message else ""
    render_html(f"""
        <div class="im-state-box im-success-state">
            <div class="im-state-icon" style="color:{COLORS.SUCCESS};">✓</div>
            <h4 class="im-state-title">{title}</h4>
            {msg_html}
        </div>
    """)


def render_partial_state(
    title: str = "Documento processado, mas alguns campos não foram identificados.",
    details: Optional[str] = None
) -> None:
    """Renderiza um PartialState quando a extração for incompleta."""
    dt_html = f"<p class='im-state-desc'>{details}</p>" if details else ""
    render_html(f"""
        <div class="im-state-box im-warning-state">
            <div class="im-state-icon" style="color:{COLORS.ATTENTION};">▲</div>
            <h4 class="im-state-title">{title}</h4>
            {dt_html}
        </div>
    """)


def render_error_state(
    title: str = "Não foi possível concluir a análise deste documento.",
    error_message: Optional[str] = None
) -> None:
    """Renderiza um ErrorState claro e compreensível."""
    err_html = f"<p class='im-state-desc' style='color:{COLORS.CRITICAL};'>{error_message}</p>" if error_message else ""
    render_html(f"""
        <div class="im-state-box im-error-state">
            <div class="im-state-icon" style="color:{COLORS.CRITICAL};">✕</div>
            <h4 class="im-state-title">{title}</h4>
            {err_html}
        </div>
    """)


def render_fallback_state(
    details: str = "Modo de contingência ativo — análise utilizando regras determinísticas regulatórias da SUSEP."
) -> None:
    """Renderiza o aviso de modo de contingência/fallback sem quebrar a confiança."""
    render_html(f"""
        <div class="im-alert im-alert-info">
            <span class="im-alert-icon">ℹ</span>
            <div class="im-alert-body">
                <b>Modo de Contingência Ativo:</b> {details}
            </div>
        </div>
    """)


def render_alert(
    text: Optional[str] = None,
    alert_type: str = "info",  # "info", "success", "attention", "critical", "legal", "warning"
    bold_prefix: Optional[str] = None,
    *,
    message: Optional[str] = None,
    level: Optional[str] = None
) -> None:
    """Renderiza um banner de alerta corporativo institucional."""
    alert_text = text if text is not None else (message or "")
    effective_type = level or alert_type or "info"
    if effective_type == "warning":
        effective_type = "attention"

    type_classes = {
        "info": "im-alert-info",
        "success": "im-alert-success",
        "attention": "im-alert-attention",
        "critical": "im-alert-critical",
        "legal": "im-alert-legal",
        "warning": "im-alert-attention"
    }
    icons = {
        "info": "ℹ",
        "success": "✓",
        "attention": "▲",
        "critical": "✕",
        "legal": "🛡️",
        "warning": "▲"
    }
    css_class = type_classes.get(effective_type, "im-alert-info")
    icon = icons.get(effective_type, "ℹ")
    prefix_html = f"<strong>{bold_prefix}</strong> " if bold_prefix else ""

    render_html(f"""
        <div class="im-alert {css_class}">
            <span class="im-alert-icon">{icon}</span>
            <div class="im-alert-body">
                {prefix_html}{alert_text}
            </div>
        </div>
    """)
