"""Agente 4 — Structurer Agent.
Responsabilidade: Conversão das seções identificadas no esquema canônico ApoliceDAO e persistência no banco SQLite.
"""
import logging
from core.schemas import DocumentState
from core.llm_client import llm_client
from core.database import db

logger = logging.getLogger(__name__)


def structurer_agent(state: DocumentState) -> DocumentState:
    """Executa o Agente 4: Mapeia dados para o modelo Pydantic ApoliceDAO e persiste no banco relacional."""
    if state.status == "concluido_em_cache":
        return state

    logger.info(f"Agente 4 (Structurer): Estruturando dados para {state.file_name}")

    try:
        # Extrai os dados normalizados via Gemini ou fallback heurístico
        apolice_dao = llm_client.extract_structured_apolice(
            raw_text=state.raw_text,
            nome_arquivo=state.file_name,
            file_hash=state.file_hash,
            metodo_extracao=state.extraction_method
        )

        # Persistência relacional com controle de idempotência
        db.save_apolice(apolice_dao)

        state.structured_data = apolice_dao
        state.status = "concluido"
        logger.info(f"Agente 4: Apólice {state.file_name} estruturada e persistida com sucesso. ID: {state.file_hash}")

    except Exception as e:
        logger.error(f"Erro no Agente 4: {e}")
        state.errors.append(f"Falha na estruturação de dados: {str(e)}")
        state.status = "erro"

    return state
