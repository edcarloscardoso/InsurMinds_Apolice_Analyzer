"""Agente 6 — Reporter Agent.
Responsabilidade: Síntese de parecer executivo narrativo em Linguagem Natural (PT-BR) via Gemini.
"""
import logging
from core.schemas import ComparisonState
from core.llm_client import llm_client
from core.database import db

logger = logging.getLogger(__name__)


def reporter_agent(state: ComparisonState) -> ComparisonState:
    """Executa o Agente 6: Elabora relatório narrativo comparativo e consolida no banco relacional."""
    logger.info("Agente 6 (Reporter): Gerando parecer executivo...")

    if not state.diff_result:
        state.errors.append("Resultado de comparação ausente para geração do relatório.")
        state.status = "erro"
        return state

    try:
        report_md = llm_client.generate_executive_report(state.diff_result)
        state.report_markdown = report_md
        state.status = "concluido"

        # Persistência do parecer e histórico de comparação
        db.save_comparison(state.diff_result, report_md)
        logger.info("Agente 6: Parecer executivo gerado e persistido com sucesso.")

    except Exception as e:
        logger.error(f"Erro no Agente 6: {e}")
        state.errors.append(f"Falha na geração do parecer executivo: {str(e)}")
        state.status = "erro"

    return state
