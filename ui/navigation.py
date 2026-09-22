"""Módulo de Navegação Centralizada do Streamlit InsurMinds.
Utiliza o padrão de versionamento dinâmico de chaves para evitar StreamlitWidgetAlreadyInstantiatedError
e garantir sincronização perfeita entre botões internos e o st.sidebar.
"""
import streamlit as st


def navigate_to(page_name: str) -> None:
    """Navega de forma atômica e consistente entre as páginas do Streamlit."""
    st.session_state["nav_page"] = page_name
    st.session_state["nav_version"] = st.session_state.get("nav_version", 0) + 1
