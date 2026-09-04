"""Agente 3 — Identifier Agent.
Responsabilidade: Segmentação e identificação de cláusulas e seções temáticas de apólices D&O.
"""
import logging
from core.schemas import DocumentState
from core.llm_client import llm_client

logger = logging.getLogger(__name__)


def identifier_agent(state: DocumentState) -> DocumentState:
    """Executa o Agente 3: Segmenta o texto bruto em categorias temáticas de D&O."""
    if state.status == "concluido_em_cache":
        return state

    logger.info(f"Agente 3 (Identifier): Segmentando cláusulas para {state.file_name}")

    if not state.raw_text:
        state.errors.append("Texto bruto vazio para identificação de cláusulas.")
        state.status = "erro"
        return state

    try:
        sections = llm_client.segment_clauses(state.raw_text)
        state.identified_sections = sections
        state.status = "clausulas_identificadas"
        logger.info(f"Agente 3: Segmentadas {len(sections)} seções com sucesso.")
    except Exception as e:
        logger.error(f"Erro no Agente 3: {e}")
        state.errors.append(f"Falha na identificação de cláusulas: {str(e)}")
        state.status = "erro"

    return state
