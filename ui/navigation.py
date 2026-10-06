"""Módulo de Navegação Centralizada do Streamlit InsurMinds.
Utiliza o padrão de versionamento dinâmico de chaves para evitar StreamlitWidgetAlreadyInstantiatedError
e garantir sincronização perfeita entre botões internos e o st.sidebar.
"""
import streamlit as st


PAGE_NORMALIZATION = {
    "upload": "Nova análise",
    "nova_analise": "Nova análise",
    "nova análise": "Nova análise",
    "comparacao": "Comparações",
    "comparação": "Comparações",
    "comparacoes": "Comparações",
    "comparações": "Comparações",
    "biblioteca": "Documentos",
    "documentos": "Documentos",
    "relatorio": "Relatórios",
    "relatório": "Relatórios",
    "relatorios": "Relatórios",
    "relatórios": "Relatórios",
    "inicio": "Início",
    "início": "Início",
    "configuracoes": "Configurações",
    "configurações": "Configurações",
    "auditoria": "Configurações",
    "auditoria contábil": "Configurações"
}


def normalize_page_name(page_name: str) -> str:
    """Normaliza o nome da página para a navegação oficial de 6 itens."""
    if not page_name:
        return "Início"
    normalized = PAGE_NORMALIZATION.get(str(page_name).strip().lower(), str(page_name).strip())
    # Valida se está na lista oficial
    valid_pages = ["Início", "Nova análise", "Comparações", "Documentos", "Relatórios", "Configurações"]
    return normalized if normalized in valid_pages else "Início"


def navigate_to(page_name: str) -> None:
    """Navega de forma atômica e consistente entre as páginas oficiais do Streamlit."""
    target = normalize_page_name(page_name)
    st.session_state["nav_page"] = target
    st.session_state["nav_version"] = st.session_state.get("nav_version", 0) + 1
