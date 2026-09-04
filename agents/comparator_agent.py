"""Agente 5 — Comparator Agent.
Responsabilidade: Execução de análise comparativa entre duas apólices D&O estruturadas.
"""
import logging
from core.schemas import ComparisonState
from core.diff_engine import compare_policies

logger = logging.getLogger(__name__)


def comparator_agent(state: ComparisonState) -> ComparisonState:
    """Executa o Agente 5: Compara campos escalares, coberturas e exclusões calculando o score de similaridade."""
    logger.info("Agente 5 (Comparator): Iniciando comparação analítica...")

    if not state.apolice_a or not state.apolice_b:
        state.errors.append("Apólices A e B devem ser fornecidas para comparação.")
        state.status = "erro"
        return state

    try:
        diff_result = compare_policies(state.apolice_a, state.apolice_b)
        state.diff_result = diff_result
        state.status = "comparado"
        logger.info(f"Agente 5: Comparação finalizada. Score de similaridade: {diff_result.score_similaridade}%")
    except Exception as e:
        logger.error(f"Erro no Agente 5: {e}")
        state.errors.append(f"Falha na comparação das apólices: {str(e)}")
        state.status = "erro"

    return state
