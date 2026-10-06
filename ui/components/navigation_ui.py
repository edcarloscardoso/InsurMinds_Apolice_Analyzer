"""Componentes de Navegação Secundária — Insurance Intelligence v1.0.
Implementa Breadcrumbs, FilterBar e Tabs corporativas.
"""
from typing import List, Dict, Optional, Callable
import streamlit as st


def render_breadcrumb(items: List[str]) -> None:
    """Renderiza uma trilha de navegação (Breadcrumb) corporativa."""
    if not items:
        return

    parts = []
    for idx, item in enumerate(items):
        if idx == len(items) - 1:
            parts.append(f"<span class='im-breadcrumb-current'>{item}</span>")
        else:
            parts.append(f"<span class='im-breadcrumb-item'>{item}</span>")
            parts.append("<span class='im-breadcrumb-sep'>/</span>")

    st.markdown(f"""
        <div class="im-breadcrumb">
            {" ".join(parts)}
        </div>
    """, unsafe_allow_html=True)


def render_filter_bar_html(
    filters: List[Dict[str, str]],
    active_key: str
) -> str:
    """Gera o HTML visual de uma FilterBar (as ações de filtro são tratadas pelos widgets do Streamlit)."""
    pills = []
    for f in filters:
        key = f.get("key", "")
        label = f.get("label", "")
        count = f.get("count", "")
        count_html = f" <span class='im-filter-count'>({count})</span>" if count else ""
        is_active = (key == active_key)
        active_cls = "im-filter-pill-active" if is_active else ""
        pills.append(f"<span class='im-filter-pill {active_cls}'>{label}{count_html}</span>")

    return f"""
    <div class="im-filter-bar">
        {" ".join(pills)}
    </div>
    """
