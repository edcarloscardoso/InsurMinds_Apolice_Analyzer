"""Agente 1 — Reception Agent.
Responsabilidade: Validação, higienização de segurança, cálculo de hash criptográfico e checagem de idempotência.
"""
from pathlib import Path
import logging
from core.schemas import DocumentState
from core.security import validate_pdf_content, compute_file_hashes, get_safe_destination_path
from core.config import UPLOADS_DIR
from core.database import db

logger = logging.getLogger(__name__)


def reception_agent(state: DocumentState) -> DocumentState:
    """Executa o Agente 1: Valida metadados, conteúdo e verifica se o documento já foi processado."""
    logger.info(f"Agente 1 (Reception): Processando arquivo {state.file_name}")

    file_path = Path(state.file_path)
    if not file_path.exists():
        state.errors.append(f"Arquivo não encontrado no caminho: {state.file_path}")
        state.status = "erro"
        return state

    try:
        file_bytes = file_path.read_bytes()
    except Exception as e:
        state.errors.append(f"Falha ao ler arquivo: {str(e)}")
        state.status = "erro"
        return state

    # Validação de segurança (tamanho, formato e magic bytes)
    is_valid, msg = validate_pdf_content(file_bytes, state.file_name)
    if not is_valid:
        state.errors.append(f"Falha na validação de segurança: {msg}")
        state.status = "erro"
        return state

    # Hashing para rastreabilidade e idempotência
    md5_hash, _ = compute_file_hashes(file_bytes)
    state.file_hash = md5_hash
    state.file_size = len(file_bytes)

    # Checagem de Idempotência no Banco de Dados
    existing_apolice = db.get_apolice_by_id(md5_hash)
    if existing_apolice:
        logger.info(f"Agente 1: Documento {state.file_name} já previamente processado (Cache Hit). ID: {md5_hash}")
        state.structured_data = existing_apolice
        state.status = "concluido_em_cache"
        return state

    state.status = "recepcionado"
    return state
