"""Definição e gerenciamento dos Perfis de Trabalho (Personas) no InsurMinds.
O perfil selecionado reside unicamente em st.session_state e customiza ordenação,
densidade e ênfase visual na camada de apresentação, sem qualquer impacto em regras de negócio ou backend.
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import streamlit as st


@dataclass(frozen=True)
class ProfileConfig:
    id: str
    label: str
    icon: str
    title: str
    tagline: str
    focus_summary: str
    default_filter: str
    density: str  # "alta", "compacta", "executiva"
    priority_relations: List[str]


PROFILES: Dict[str, ProfileConfig] = {
    "analista": ProfileConfig(
        id="analista",
        label="Analista de Seguros",
        icon="🔍",
        title="Perfil: Analista Técnico de Seguros",
        tagline="Foco em profundidade analítica, granularidade de cláusulas e rastreabilidade integral.",
        focus_summary="Diferenças detalhadas → Evidências literais → Metadados documentais",
        default_filter="todas",
        density="alta",
        priority_relations=[
            "changed_condition",
            "changed_scope",
            "changed_limit",
            "different",
            "broader",
            "narrower",
            "semantic_equivalent"
        ]
    ),
    "subscritor": ProfileConfig(
        id="subscritor",
        label="Subscritor / Underwriter",
        icon="⚖️",
        title="Perfil: Subscritor / Underwriter",
        tagline="Foco em exposição de risco, limitações de cobertura e restrições de garantias.",
        focus_summary="Alterações de condição/escopo/limite → Exclusões → Diferenças críticas",
        default_filter="relevantes",
        density="compacta",
        priority_relations=[
            "changed_scope",
            "changed_condition",
            "changed_limit",
            "different",
            "narrower",
            "broader",
            "semantic_equivalent"
        ]
    ),
    "corretor": ProfileConfig(
        id="corretor",
        label="Corretor de Seguros",
        icon="🤝",
        title="Perfil: Corretor de Seguros",
        tagline="Foco em confronto A/B, garantias exclusivas de cada documento e síntese executiva para tomada de decisão.",
        focus_summary="Comparações A/B → Garantias exclusivas → Síntese executiva",
        default_filter="exclusivas",
        density="executiva",
        priority_relations=[
            "broader",
            "changed_limit",
            "different",
            "changed_scope",
            "changed_condition",
            "narrower",
            "semantic_equivalent"
        ]
    ),
    "juridico": ProfileConfig(
        id="juridico",
        label="Jurídico / Compliance",
        icon="🏛️",
        title="Perfil: Jurídico & Compliance Regulatório",
        tagline="Foco em redação contratual literal, aderência às circulares SUSEP e cadeia de custódia.",
        focus_summary="Alterações substantivas → Evidências literais auditadas → Pareceres",
        default_filter="relevantes",
        density="alta",
        priority_relations=[
            "changed_condition",
            "different",
            "changed_scope",
            "changed_limit",
            "narrower",
            "broader",
            "semantic_equivalent"
        ]
    ),
    "visitante": ProfileConfig(
        id="visitante",
        label="Explorar como visitante",
        icon="🌐",
        title="Perfil: Modo Visitante",
        tagline="Visão panorâmica equilibrada para exploração institucional da plataforma.",
        focus_summary="Visão geral → Principais diferenças → Amostra de evidências",
        default_filter="todas",
        density="compacta",
        priority_relations=[
            "changed_scope",
            "changed_condition",
            "different",
            "broader",
            "narrower",
            "changed_limit",
            "semantic_equivalent"
        ]
    )
}

DEFAULT_PROFILE_ID = "analista"


def get_active_profile() -> ProfileConfig:
    """Retorna o ProfileConfig ativo na sessão atual."""
    profile_id = st.session_state.get("user_profile", DEFAULT_PROFILE_ID)
    if profile_id not in PROFILES:
        profile_id = DEFAULT_PROFILE_ID
        st.session_state["user_profile"] = profile_id
    return PROFILES[profile_id]


def set_active_profile(profile_id: str) -> None:
    """Define o ProfileConfig ativo na sessão atual."""
    if profile_id in PROFILES:
        st.session_state["user_profile"] = profile_id


def get_profile_metadata(profile_id: Optional[str] = None) -> ProfileConfig:
    """Recupera metadados de um perfil específico ou do ativo."""
    if profile_id and profile_id in PROFILES:
        return PROFILES[profile_id]
    return get_active_profile()


def filter_and_sort_differences_for_profile(
    matches: List[Any],
    profile_id: Optional[str] = None
) -> List[Any]:
    """Ordena uma lista de SemanticMatchItem conforme a ordem de prioridade da persona ativa.

    NUNCA altera o conteúdo, dados, classificação ou evidência de nenhum item.
    Apenas reorganiza a sequência de visualização para atender ao foco do profissional.
    """
    config = get_profile_metadata(profile_id)
    priority_map = {rel: idx for idx, rel in enumerate(config.priority_relations)}

    def sort_key(item):
        rel = getattr(item, "relation", "")
        return priority_map.get(rel, 999)

    return sorted(matches, key=sort_key)
