"""Módulo de Componentes Reutilizáveis — Insurance Intelligence v1.0.
Padroniza a apresentação visual de toda a aplicação conforme a especificação oficial de frontend.
"""
from ui.components.badges import (
    SEMANTIC_RELATION_CONFIG,
    render_semantic_badge,
    render_status_badge
)
from ui.components.cards import (
    render_card_start,
    render_card_end,
    render_metric_card,
    render_difference_card_html
)
from ui.components.evidence import (
    render_evidence_panel,
    render_evidence_snippet_html
)
from ui.components.states import (
    render_empty_state,
    render_loading_state,
    render_success_state,
    render_partial_state,
    render_error_state,
    render_fallback_state,
    render_alert
)
from ui.components.navigation_ui import (
    render_breadcrumb,
    render_filter_bar_html
)
from ui.components.app_shell import (
    render_app_shell,
    render_sidebar,
    render_topbar,
    render_profile_selector,
    OFFICIAL_NAVIGATION
)
from ui.components.context_assistant import (
    render_context_assistant,
    get_assistant_context
)

__all__ = [
    "SEMANTIC_RELATION_CONFIG",
    "render_semantic_badge",
    "render_status_badge",
    "render_card_start",
    "render_card_end",
    "render_metric_card",
    "render_difference_card_html",
    "render_evidence_panel",
    "render_evidence_snippet_html",
    "render_empty_state",
    "render_loading_state",
    "render_success_state",
    "render_partial_state",
    "render_error_state",
    "render_fallback_state",
    "render_alert",
    "render_breadcrumb",
    "render_filter_bar_html",
    "render_app_shell",
    "render_sidebar",
    "render_topbar",
    "render_profile_selector",
    "OFFICIAL_NAVIGATION",
    "render_context_assistant",
    "get_assistant_context"
]
