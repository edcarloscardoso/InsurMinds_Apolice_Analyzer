"""Componente AppShell — Insurance Intelligence v1.0.
Estrutura o layout principal corporativo: Sidebar compacta, TopBar com seletor de perfil,
Breadcrumb e ContentArea.
"""
from typing import Optional, Dict, Any, Callable
import streamlit as st

from ui.tokens import COLORS
from ui.persona.profiles import (
    PROFILES,
    get_active_profile,
    set_active_profile,
    DEFAULT_PROFILE_ID
)
from ui.navigation import navigate_to
from ui.components.navigation_ui import render_breadcrumb


OFFICIAL_NAVIGATION = [
    {"id": "inicio", "label": "Início", "icon": "🏠"},
    {"id": "nova_analise", "label": "Nova análise", "icon": "＋"},
    {"id": "comparacoes", "label": "Comparações", "icon": "⚖️"},
    {"id": "documentos", "label": "Documentos", "icon": "📑"},
    {"id": "relatorios", "label": "Relatórios", "icon": "📄"},
    {"id": "configuracoes", "label": "Configurações", "icon": "⚙️"}
]


def render_profile_selector() -> None:
    """Renderiza o seletor de perfil corporativo na TopBar, persistido em st.session_state."""
    active_profile = get_active_profile()
    profile_options = list(PROFILES.keys())

    # Índice atual
    current_idx = profile_options.index(active_profile.id) if active_profile.id in profile_options else 0

    selected_id = st.selectbox(
        "Perfil de Trabalho:",
        options=profile_options,
        index=current_idx,
        format_func=lambda pid: f"{PROFILES[pid].icon} {PROFILES[pid].label}",
        key="topbar_profile_select",
        label_visibility="collapsed"
    )

    if selected_id != st.session_state.get("user_profile"):
        set_active_profile(selected_id)
        st.rerun()


def render_topbar(current_nav_label: str) -> None:
    """Renderiza a barra superior (TopBar) institucional com identidade e ProfileSelector."""
    active_profile = get_active_profile()

    col_brand, col_prof, col_asst = st.columns([2.9, 1.4, 0.7])
    with col_brand:
        st.markdown(f"""
            <div class="im-topbar-brand">
                <div class="im-topbar-title-group">
                    <span class="im-topbar-badge">INSURANCE INTELLIGENCE</span>
                    <h2 class="im-topbar-title">🛡️ InsurMinds · Plataforma Analítica D&O</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)
        crumb_items = ["InsurMinds", current_nav_label]
        if current_nav_label == "Comparações" and st.session_state.get("viewing_diff_idx") is not None:
            crumb_items.append("Detalhe da Diferença")
        render_breadcrumb(crumb_items)
    with col_prof:
        st.markdown("""
            <div style="text-align: right; margin-bottom: 2px;">
                <span style="font-size: 11px; font-weight: 700; color: #6B7785; text-transform: uppercase; letter-spacing: 0.5px;">
                    Perfil de Trabalho Ativo:
                </span>
            </div>
        """, unsafe_allow_html=True)
        render_profile_selector()
        st.markdown(f"""
            <div style="text-align: right; margin-top: 4px;">
                <span class="im-profile-tagline" title="{active_profile.focus_summary}">
                    {active_profile.icon} {active_profile.tagline}
                </span>
            </div>
        """, unsafe_allow_html=True)

    with col_asst:
        is_asst_open = st.session_state.get("context_assistant_open", False)
        asst_btn_label = "✕ Fechar" if is_asst_open else "🧠 Assistente"
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        if st.button(asst_btn_label, key="topbar_assistant_btn", help="Abrir ou fechar o Assistente Contextual D&O"):
            st.session_state["context_assistant_open"] = not is_asst_open
            st.rerun()

    st.markdown("<hr class='im-topbar-divider'/>", unsafe_allow_html=True)


def render_sidebar(current_page: str, on_navigate: Optional[Callable[[str], None]] = None) -> str:
    """Renderiza a barra lateral (Sidebar) compacta com a navegação oficial de 6 itens."""
    nav_labels = [item["label"] for item in OFFICIAL_NAVIGATION]
    nav_icons = {item["label"]: item["icon"] for item in OFFICIAL_NAVIGATION}

    # Mapeamento de retrocompatibilidade
    legacy_to_official = {
        "Upload": "Nova análise",
        "Comparação": "Comparações",
        "Biblioteca": "Documentos",
        "Relatório": "Relatórios",
        "Auditoria Contábil": "Configurações",
        "Início": "Início",
        "Nova análise": "Nova análise",
        "Comparações": "Comparações",
        "Documentos": "Documentos",
        "Relatórios": "Relatórios",
        "Configurações": "Configurações"
    }

    normalized_current = legacy_to_official.get(current_page, "Início")
    current_idx = nav_labels.index(normalized_current) if normalized_current in nav_labels else 0

    with st.sidebar:
        # Header da Sidebar
        st.markdown("""
            <div class="im-sidebar-header">
                <div class="im-logo-icon">🛡️</div>
                <div class="im-logo-title">InsurMinds</div>
                <div class="im-logo-sub">Insurance Intelligence v1.0</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='im-nav-section-label'>NAVEGAÇÃO PRINCIPAL</div>", unsafe_allow_html=True)

        radio_key = f"nav_radio_v_{st.session_state.get('nav_version', 0)}"
        escolha = st.radio(
            "Navegação:",
            options=nav_labels,
            index=current_idx,
            key=radio_key,
            format_func=lambda x: f"{nav_icons[x]} {x}",
            label_visibility="collapsed"
        )

        if escolha != normalized_current:
            if on_navigate:
                on_navigate(escolha)
            else:
                st.session_state["nav_page"] = escolha
                st.session_state["nav_version"] = st.session_state.get("nav_version", 0) + 1
            st.rerun()

        # Botão de Acesso Rápido ao Assistente Contextual
        is_asst_open = st.session_state.get("context_assistant_open", False)
        asst_side_label = "✕ Fechar Assistente" if is_asst_open else "🧠 Assistente Contextual"
        if st.button(asst_side_label, key="sidebar_assistant_btn", use_container_width=True, help="Abrir ou fechar o Assistente Contextual D&O"):
            st.session_state["context_assistant_open"] = not is_asst_open
            st.rerun()

        st.markdown("<hr class='im-sidebar-divider'/>", unsafe_allow_html=True)

        # Status Discreto do Sistema
        st.markdown("<div class='im-nav-section-label'>INFRAESTRUTURA ANALÍTICA</div>", unsafe_allow_html=True)

        from core.llm_client import llm_client
        from core.database import db
        from core.config import GEMINI_MODEL

        if llm_client.is_available():
            st.markdown(f"""
                <div class="im-system-status im-status-online">
                    <span class="im-status-dot-green"></span>
                    <div>
                        <div class="im-status-name">Interpretação Assistida Ativa</div>
                        <div class="im-status-model">{GEMINI_MODEL}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="im-system-status im-status-fallback">
                    <span class="im-status-dot-blue"></span>
                    <div>
                        <div class="im-status-name">Modo de Contingência</div>
                        <div class="im-status-model">Motor Heurístico D&O</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        total_docs = len(db.list_apolices())
        st.markdown(f"""
            <div class="im-sidebar-meta">
                <div>• Repositório: <b>{total_docs} documentos</b></div>
                <div>• Padrão: <b>SUSEP Ramo 0378 (D&O)</b></div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr class='im-sidebar-divider'/>", unsafe_allow_html=True)
        st.caption("InsurMinds · I2A2 (2026)")

    return escolha


def render_app_shell(current_page: str, on_navigate: Optional[Callable[[str], None]] = None) -> str:
    """Invoca o AppShell completo: Sidebar + TopBar."""
    active_nav = render_sidebar(current_page, on_navigate)
    render_topbar(active_nav)
    return active_nav
