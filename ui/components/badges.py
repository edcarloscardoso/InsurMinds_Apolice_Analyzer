"""Componentes de Badges do InsurMinds — Insurance Intelligence v1.0.
Implementa StatusBadge e SemanticBadge mapeando estritamente as 7 relações semânticas canônicas.
"""
from typing import Dict, Any, Optional
from ui.tokens import COLORS


# Mapeamento canônico das 7 relações semânticas com rótulos em português corporativo
# Mantém compatibilidade integral com o teste test_fase6_semantic_relation_config_covers_all_seven_types
SEMANTIC_RELATION_CONFIG: Dict[str, Dict[str, str]] = {
    "semantic_equivalent": {
        "label": "Equivalente",
        "badge_class": "badge-sem-equiv",
        "icon": "✓",
        "desc": "Cláusulas com redação e efeitos contratuais substancialmente equivalentes.",
        "bg_color": "#E6F4EA",
        "text_color": "#197B5C",
        "border_color": "#A3D9B5"
    },
    "different": {
        "label": "Diferente",
        "badge_class": "badge-sem-diff",
        "icon": "✕",
        "desc": "Conceitos juridicamente distintos ou sem correspondência equivalente.",
        "bg_color": "#FDE8E8",
        "text_color": "#D94A4A",
        "border_color": "#F8B4B4"
    },
    "broader": {
        "label": "Escopo ampliado",
        "badge_class": "badge-sem-broader",
        "icon": "▲",
        "desc": "A cobertura A possui abrangência mais ampla que a modalidade de B.",
        "bg_color": "#E0F2F1",
        "text_color": "#0B8A84",
        "border_color": "#80CBC4"
    },
    "narrower": {
        "label": "Escopo reduzido",
        "badge_class": "badge-sem-narrower",
        "icon": "▼",
        "desc": "A cobertura A possui escopo mais restrito comparado à abrangência de B.",
        "bg_color": "#EFF6FF",
        "text_color": "#2864C7",
        "border_color": "#BFDBFE"
    },
    "changed_scope": {
        "label": "Escopo alterado",
        "badge_class": "badge-sem-scope",
        "icon": "⚠️",
        "desc": "Mesmo conceito com ressalvas, exclusões internas ou redação substancialmente alterada.",
        "bg_color": "#FEF3C7",
        "text_color": "#B45309",
        "border_color": "#FCD34D"
    },
    "changed_condition": {
        "label": "Condição alterada",
        "badge_class": "badge-sem-cond",
        "icon": "📋",
        "desc": "Exigências procedimentais, prazos ou condições de acionamento divergentes.",
        "bg_color": "#F3E8FF",
        "text_color": "#7E22CE",
        "border_color": "#D8B4FE"
    },
    "changed_limit": {
        "label": "Limite alterado",
        "badge_class": "badge-sem-limit",
        "icon": "💲",
        "desc": "Mesma cobertura com limites financeiros ou percentuais assimétricos.",
        "bg_color": "#E0E7FF",
        "text_color": "#3730A3",
        "border_color": "#C7D2FE"
    }
}


def render_semantic_badge(relation: str, show_icon: bool = True) -> str:
    """Gera o HTML do badge semântico corporativo para uma das 7 relações canônicas."""
    cfg = SEMANTIC_RELATION_CONFIG.get(relation, {
        "label": relation,
        "badge_class": "badge-sem-neutral",
        "icon": "•",
        "desc": "",
        "bg_color": "#F3F4F6",
        "text_color": "#4B5563",
        "border_color": "#E5E7EB"
    })

    icon_html = f"<span class='badge-icon'>{cfg['icon']}</span> " if show_icon else ""
    return (
        f"<span class='im-badge {cfg['badge_class']}' "
        f"style='background-color:{cfg['bg_color']}; color:{cfg['text_color']}; border-color:{cfg['border_color']};' "
        f"title='{cfg['desc']}'>"
        f"{icon_html}{cfg['label']}"
        f"</span>"
    )


def render_status_badge(status_type: str, text: str) -> str:
    """Gera um StatusBadge corporativo discreto (success, attention, critical, info, neutral)."""
    type_styles = {
        "success": {"bg": "#E6F4EA", "color": "#197B5C", "border": "#A3D9B5", "icon": "●"},
        "attention": {"bg": "#FEF3C7", "color": "#B45309", "border": "#FCD34D", "icon": "▲"},
        "critical": {"bg": "#FDE8E8", "color": "#D94A4A", "border": "#F8B4B4", "icon": "■"},
        "info": {"bg": "#E0F2F1", "color": "#0B8A84", "border": "#80CBC4", "icon": "ℹ"},
        "neutral": {"bg": "#F1F5F9", "color": "#475569", "border": "#CBD5E1", "icon": "○"}
    }
    st_style = type_styles.get(status_type, type_styles["neutral"])
    return (
        f"<span class='im-status-badge' "
        f"style='background-color:{st_style['bg']}; color:{st_style['color']}; border-color:{st_style['border']};'>"
        f"<span class='status-dot'>{st_style['icon']}</span> {text}"
        f"</span>"
    )
